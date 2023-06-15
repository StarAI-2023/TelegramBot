import asyncio
import random
import string
import time


# Generate 16k words for each user
def generate_text():
    words = string.ascii_lowercase
    return " ".join(random.choice(words) for _ in range(32 * 1000))


# Perform operation on the text
def perform_operation(text):
    return len(set(text.split(" ")))


# Simulate a user request
async def simulate_user_request(_):
    text = generate_text()
    result = perform_operation(text)
    return result


async def main():
    start = time.time()
    num_users = 1000

    tasks = [simulate_user_request(i) for i in range(num_users)]
    await asyncio.gather(*tasks)

    print(f"Time taken for {num_users} users: {time.time() - start} seconds")


if __name__ == "__main__":
    asyncio.run(main())


# Time taken for 1000 users: 13 seconds

# This script is more representative of a single-threaded server handling 1000 requests, assuming the operations are non-blocking
# (which is simulated here by CPU-bound operations). The time taken is 13 seconds, which is... okay? I guess? I don't know what
