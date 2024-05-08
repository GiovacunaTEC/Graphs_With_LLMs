import openai
import streamlit as st
import os
from timeit import default_timer as timer

from langchain_community.graphs import Neo4jGraph
from langchain.chains import GraphCypherQAChain
from langchain.prompts.prompt import PromptTemplate
from langchain_openai import ChatOpenAI
from langchain.prompts import ChatPromptTemplate

from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Cypher generation prompt
cypher_generation_template = """
You are an expert Neo4j Cypher translator who converts English to Cypher based on the Neo4j Schema provided, following the instructions below:
1. Generate Cypher query compatible ONLY for Neo4j Version 5
2. Do not use EXISTS, SIZE, HAVING keywords in the cypher. Use alias when using the WITH keyword
3. Use only Nodes and relationships mentioned in the schema
4. Always do a case-insensitive and fuzzy search for any properties related search. Eg: to search for a Client, use `toLower(client.id) contains 'neo4j'`. To search for Slack Messages, use 'toLower(SlackMessage.text) contains 'neo4j'`. To search for a project, use `toLower(project.summary) contains 'logistics platform' OR toLower(project.name) contains 'logistics platform'`.)
5. Never use relationships that are not mentioned in the given schema
6. When asked about projects, Match the properties using case-insensitive matching and the OR-operator, E.g, to find a logistics platform -project, use `toLower(project.summary) contains 'logistics platform' OR toLower(project.name) contains 'logistics platform'`.

schema: {schema}

Examples:
Question: Which client's projects use most of our people?
Answer: ```MATCH (c:CLIENT)<-[:HAS_CLIENT]-(p:Project)-[:HAS_PEOPLE]->(person:Person)
RETURN c.name AS Client, COUNT(DISTINCT person) AS NumberOfPeople
ORDER BY NumberOfPeople DESC```
Question: Which person uses the largest number of different technologies?
Answer: ```MATCH (person:Person)-[:USES_TECH]->(tech:Technology)
RETURN person.name AS PersonName, COUNT(DISTINCT tech) AS NumberOfTechnologies
ORDER BY NumberOfTechnologies DESC```

Question: {question}
"""

cypher_prompt = PromptTemplate(
    template = cypher_generation_template,
    input_variables = ["schema", "question"]
)

CYPHER_QA_TEMPLATE = """You are an assistant that helps to form nice and human understandable answers.
The information part contains the provided information that you must use to construct an answer.
The provided information is authoritative, you must never doubt it or try to use your internal knowledge to correct it.
Make the answer sound as a response to the question. Do not mention that you based the result on the given information.
If the provided information is empty, say that you don't know the answer.
Final answer should be easily readable and structured.
Information:
{context}

Question: {question}
Helpful Answer:"""

qa_prompt = PromptTemplate(
    input_variables=["context", "question"], template=CYPHER_QA_TEMPLATE
)

def query_graph(user_input):
    graph = Neo4jGraph(
        url="neo4j+s://67532d48.databases.neo4j.io:7687", 
        username="neo4j", 
        password="_Tl03SeAXq6knZkSH6d7y6YrrwNM8GBOZ-1R3m3cUQ4"
        )
    chain = GraphCypherQAChain.from_llm(
        ChatOpenAI(temperature=0, openai_api_key="sk-proj-lyrnskHOb6O6H29hsc2lT3BlbkFJ67QfmWM89UkSitmLYmXn"),
        graph=graph, 
        verbose=True,
        return_intermediate_steps=True,
        cypher_prompt=cypher_prompt,
        qa_prompt=qa_prompt
            )
    result = chain(user_input)
    return result

st.set_page_config(layout="wide")

if "user_msgs" not in st.session_state:
    st.session_state.user_msgs = []
if "system_msgs" not in st.session_state:
    st.session_state.system_msgs = []

title_col, empty_col, img_col = st.columns([2, 1, 2])    

with title_col:
    st.title("Conversational Neo4J Assistant")
with img_col:
    st.image("https://dist.neo4j.com/wp-content/uploads/20210423062553/neo4j-social-share-21.png", width=200)

user_input = st.text_input("Enter your question", key="input")
if user_input:
    with st.spinner("Processing your question..."):
        st.session_state.user_msgs.append(user_input)
        start = timer()
        
        result = {"result": "Default answer in case of early failure or exception."}  # Default initialization

        try:
            result = query_graph(user_input)
            
            # intermediate_steps = result["intermediate_steps"]
            # cypher_query = intermediate_steps[0]["query"]
            # database_results = intermediate_steps[1]["context"]

            answer = result["result"]
            st.session_state.system_msgs.append(answer)
        except Exception as e:
            # st.write("Failed to process question. Please try again.")
            # print(e)
            
            result = {"result": f"Error processing the request: {str(e)}"}

            
            
    st.write(f"Time taken: {timer() - start:.2f}s")
    st.write("Answer:", result["result"])

    col1, col2, col3 = st.columns([1, 1, 1])

def message(text, is_user=False, key=None):
    if is_user:
        st.markdown(f"> **User:** {text}", unsafe_allow_html=True, key=key)
    else:
        st.markdown(f"> **Assistant:** {text}", unsafe_allow_html=True, key=key)
    
    # Display the chat history
    with col1:
        if st.session_state["system_msgs"]:
            for i in range(len(st.session_state["system_msgs"]) - 1, -1, -1):
                message(st.session_state["system_msgs"][i], key = str(i) + "_assistant")
                message(st.session_state["user_msgs"][i], is_user=True, key=str(i) + "_user")

    with col2:
        if cypher_query:
            st.text_area("Last Cypher Query", cypher_query, key="_cypher", height=240)
        
    with col3:
        if database_results:
            st.text_area("Last Database Results", database_results, key="_database", height=240)