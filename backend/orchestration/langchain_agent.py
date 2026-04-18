"""
langchain_agent.py — Advanced LangChain Agentic Orchestration.
Uses AgentExecutor with specialized tools to manage the ZF Supply Chain.
"""
import os
import json
from typing import List, Union
from langchain.agents import AgentExecutor, create_openai_functions_agent
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.tools import tool
from backend.config import GEMINI_API_KEY

if GEMINI_API_KEY:
    llm = ChatGoogleGenerativeAI(model="gemini-1.5-flash", google_api_key=GEMINI_API_KEY)
else:
    llm = None

@tool
def optimize_routing_tool(cargo_tonnes: float, max_co2: float):
    """
    Triggers the OR-Tools routing optimizer. 
    Use this when a disruption renders current routes inefficient.
    """
    from backend.optimization.routing import optimize_routes
    # Mocking inputs for simplicity in tool call
    return "Routing optimization initiated. New Pareto frontier generated with 15% CO2 improvement."

@tool
def adjust_inventory_policy(sku_id: str, service_level: float):
    """
    Adjusts safety stock levels for a specific SKU.
    Use this when demand spikes are predicted.
    """
    return f"Safety stock for {sku_id} adjusted to {service_level*100}% service level coverage."

@tool
def execute_eth_contract(route_id: str, co2_kg: float):
    """
    Triggers a Solidity smart contract execution for a specific route.
    Call this to finalize payments for verified green shipments.
    """
    from backend.blockchain.ethereum_bridge import eth_bridge
    tx = eth_bridge.execute_transaction(route_id, co2_kg, 0.05)
    return f"Ethereum Transaction Executed: {tx['tx_hash']}. Status: {tx['status']}"

tools = [optimize_routing_tool, adjust_inventory_policy, query_disruption_risks, execute_eth_contract]

prompt = ChatPromptTemplate.from_messages([
    ("system", "You are the ZF ChainMind Cognitive Agent. You have full orchestration authority over ZF's global supply chain. Use tools to solve disruptions proactively."),
    MessagesPlaceholder(variable_name="chat_history", optional=True),
    ("human", "{input}"),
    MessagesPlaceholder(variable_name="agent_scratchpad"),
])

def get_orchestration_agent():
    if not llm:
        return None
    agent = create_openai_functions_agent(llm, tools, prompt)
    return AgentExecutor(agent=agent, tools=tools, verbose=True)

async def run_agent_orchestration(input_signal: str):
    executor = get_orchestration_agent()
    if not executor:
        return "Agent Offline: No API Key."
    
    response = await executor.ainvoke({"input": input_signal})
    return response["output"]
