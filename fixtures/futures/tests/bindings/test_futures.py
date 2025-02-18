from futures import *
import unittest
from datetime import datetime
import asyncio

def now():
    return datetime.now()

class TestFutures(unittest.TestCase):
    def test_always_ready(self):
        async def test():
            self.assertEqual(await always_ready(), True)

        asyncio.run(test())

    def test_void(self):
        async def test():
            self.assertEqual(await void(), None)

        asyncio.run(test())

    def test_sleep(self):
        async def test():
            t0 = now()
            await sleep(2000)
            t1 = now()

            t_delta = (t1 - t0).total_seconds()
            self.assertGreater(t_delta, 2)

        asyncio.run(test())

    def test_sequential_futures(self):
        async def test():
            t0 = now()
            result_alice = await say_after(100, 'Alice')
            result_bob = await say_after(200, 'Bob')
            t1 = now()

            t_delta = (t1 - t0).total_seconds()
            self.assertGreater(t_delta, 0.3)
            self.assertEqual(result_alice, 'Hello, Alice!')
            self.assertEqual(result_bob, 'Hello, Bob!')

        asyncio.run(test())

    def test_concurrent_tasks(self):
        async def test():
            alice = asyncio.create_task(say_after(100, 'Alice'))
            bob = asyncio.create_task(say_after(200, 'Bob'))

            t0 = now()
            result_alice = await alice
            result_bob = await bob
            t1 = now()

            t_delta = (t1 - t0).total_seconds()
            self.assertGreater(t_delta, 0.2)
            self.assertEqual(result_alice, 'Hello, Alice!')
            self.assertEqual(result_bob, 'Hello, Bob!')

        asyncio.run(test())

    def test_async_methods(self):
        async def test():
            megaphone = new_megaphone()
            t0 = now()
            result_alice = await megaphone.say_after(200, 'Alice')
            t1 = now()

            t_delta = (t1 - t0).total_seconds()
            self.assertGreater(t_delta, 0.2)
            self.assertEqual(result_alice, 'HELLO, ALICE!')

        asyncio.run(test())

    def test_with_tokio_runtime(self):
        async def test():
            t0 = now()
            result_alice = await say_after_with_tokio(200, 'Alice')
            t1 = now()

            t_delta = (t1 - t0).total_seconds()
            self.assertGreater(t_delta, 0.2)
            self.assertEqual(result_alice, 'Hello, Alice (with Tokio)!')

        asyncio.run(test())

    def test_fallible(self):
        async def test():
            result = await fallible_me(False)
            self.assertEqual(result, 42)

            try:
                result = await fallible_me(True)
                self.assertTrue(False) # should never be reached
            except MyError as exception:
                self.assertTrue(True)

            megaphone = new_megaphone()

            result = await megaphone.fallible_me(False)
            self.assertEqual(result, 42)

            try:
                result = await megaphone.fallible_me(True)
                self.assertTrue(False) # should never be reached
            except MyError as exception:
                self.assertTrue(True)

        asyncio.run(test())

    def test_fallible_struct(self):
        async def test():
            megaphone = await fallible_struct(False)
            self.assertEqual(await megaphone.fallible_me(False), 42)

            try:
                await fallible_struct(True)
                self.assertTrue(False) # should never be reached
            except MyError as exception:
                pass

        asyncio.run(test())

    def test_record(self):
        async def test():
            result = await new_my_record("foo", 42)
            self.assertEqual(result.__class__, MyRecord)
            self.assertEqual(result.a, "foo")
            self.assertEqual(result.b, 42)

        asyncio.run(test())

    def test_cancel(self):
        async def test():
            # Create a task
            task = asyncio.create_task(say_after(200, 'Alice'))
            # Wait to ensure that the polling has started, then cancel the task
            await asyncio.sleep(0.1)
            task.cancel()
            # Wait long enough for the Rust callback to fire.  This shouldn't cause an exception,
            # even though the task is cancelled.
            await asyncio.sleep(0.2)
            # Awaiting the task should result in a CancelledError.
            with self.assertRaises(asyncio.CancelledError):
                await task

        asyncio.run(test())

    # Test a future that uses a lock and that is cancelled.
    def test_shared_resource_cancellation(self):
        # Note: Python uses the event loop to schedule calls via the `call_soon_threadsafe()`
        # method.  This means that creating a task and cancelling it won't trigger the issue, we
        # need to create an EventLoop and close it instead.
        loop = asyncio.new_event_loop()
        loop.create_task(use_shared_resource(
            SharedResourceOptions(release_after_ms=100, timeout_ms=1000)))
        # Wait some time to ensure the task has locked the shared resource
        loop.call_later(0.05, loop.stop)
        loop.run_forever()
        # Close the EventLoop before the shared resource has been released.
        loop.close()

        # Try accessing the shared resource again using the main event loop.  The initial task
        # should release the shared resource before the timeout expires.
        asyncio.run(use_shared_resource(SharedResourceOptions(release_after_ms=0, timeout_ms=1000)))

    def test_shared_resource_no_cancellation(self):
        async def test():
            await use_shared_resource(SharedResourceOptions(release_after_ms=100, timeout_ms=1000))
            await use_shared_resource(SharedResourceOptions(release_after_ms=0, timeout_ms=1000))
        asyncio.run(test())

if __name__ == '__main__':
    unittest.main()
