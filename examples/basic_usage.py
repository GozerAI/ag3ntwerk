"""
Basic usage example for ag3ntwerk.

This example demonstrates how to:
1. Connect to GPT4All
2. Initialize the Nexus (control plane) with all agents
3. Execute tasks through the full ag3ntwerk

The initialization factory handles wiring all 14 active agents to the Nexus,
establishing proper hierarchy for routing and learning.

Prerequisites:
- GPT4All Desktop running with API server enabled
  (Settings > Application > Advanced > Enable Local API Server)
"""

import asyncio
from ag3ntwerk.llm.gpt4all_provider import GPT4AllProvider
from ag3ntwerk.initialization import create_coo_with_executives
from ag3ntwerk.core.base import Task, TaskPriority


async def main():
    # Initialize LLM provider
    print("Connecting to GPT4All...")
    llm = GPT4AllProvider()

    if not await llm.connect():
        print("Failed to connect to GPT4All!")
        print("Make sure GPT4All Desktop is running with API server enabled.")
        print("(Settings > Application > Advanced > Enable Local API Server)")
        return

    print(f"Connected! Available models: {[m.name for m in llm.available_models]}")

    # Initialize Nexus with all agents using centralized factory
    # This automatically wires all 14 active agents to the Nexus
    coo = create_coo_with_executives(llm_provider=llm)

    print(f"Registered {len(coo.subordinates)} agents: {[a.code for a in coo.subordinates]}")

    # Example 1: Security scan task (routes to Sentinel)
    print("\n--- Example 1: Security Task ---")
    security_task = Task(
        description="Analyze the security of a basic login function",
        task_type="security_scan",
        priority=TaskPriority.HIGH,
        context={
            "code": """
def login(username, password):
    query = f"SELECT * FROM users WHERE username='{username}' AND password='{password}'"
    result = db.execute(query)
    return result.fetchone()
            """,
            "target": "login.py",
        },
    )

    result = await coo.execute(security_task)
    print(f"Task success: {result.success}")
    if result.output:
        print(f"Analysis:\n{result.output.get('analysis', result.output)[:500]}...")

    # Example 2: Code review task (routes to Forge)
    print("\n--- Example 2: Code Review Task ---")
    review_task = Task(
        description="Review this Python function for best practices",
        task_type="code_review",
        priority=TaskPriority.MEDIUM,
        context={
            "code": """
def calculate_total(items):
    total = 0
    for i in range(len(items)):
        total = total + items[i]['price'] * items[i]['quantity']
    return total
            """,
            "file": "cart.py",
        },
    )

    result = await coo.execute(review_task)
    print(f"Task success: {result.success}")
    if result.output:
        print(f"Review:\n{result.output.get('review', result.output)[:500]}...")

    # Example 3: Direct query to Nexus
    print("\n--- Example 3: System Status ---")
    status = await coo.get_system_status()
    print(f"System status: {status}")

    # Cleanup
    await llm.disconnect()
    print("\nDisconnected from GPT4All")


if __name__ == "__main__":
    asyncio.run(main())
