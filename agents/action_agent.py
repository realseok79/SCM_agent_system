class ActionAgent:
    def __init__(self):
        print("ActionAgent initialized")

    def execute_order(self, analysis):
        # Mock ordering
        print(f"Executing order based on: {analysis}")
        return {"order_id": "ORD-001", "quantity": 100}
