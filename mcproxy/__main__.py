import proxy
import asyncio

if __name__ == "__main__":
    try:
        asyncio.run(proxy.main())
    except KeyboardInterrupt:
        print("interrupt")