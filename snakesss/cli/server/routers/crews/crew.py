from crewai import Agent, Task, Crew, Process
from crewai.project import CrewBase, agent, crew, task
from pydantic import BaseModel
from typing import List


class Wardrobe(BaseModel):
    top: str
    bottom: str
    shoes: str
    accessories: List[str]


class WeatherCondition(BaseModel):
    date: str
    temperature: str
    conditions: str
    wardrobe: Wardrobe


class ClothingRecommendation(BaseModel):
    location: str
    weather_conditions: List[WeatherCondition]


class TripPlanCrewOutput(BaseModel):
    recommendations: List[ClothingRecommendation]


@CrewBase
class TravelCrew:
    agents_config = "config/agents.yaml"  # type: ignore
    tasks_config = "config/tasks.yaml"

    @agent
    def location_agent(self) -> Agent:
        return Agent(
            config=self.agents_config["location_agent"],
        )

    @agent
    def weather_agent(self) -> Agent:
        return Agent(
            config=self.agents_config["weather_agent"],
        )

    @task
    def weather_forecast(self) -> Task:
        return Task(
            config=self.tasks_config["weather_forecast"],
        )

    @agent
    def fashion_agent(self) -> Agent:
        return Agent(
            config=self.agents_config["fashion_agent"],
        )

    @task
    def location_task(self) -> Task:
        return Task(
            config=self.tasks_config["location_task"],
        )

    @task
    def clothing_recommendation(self) -> Task:
        return Task(config=self.tasks_config["clothing_recommendation"], output_json=TripPlanCrewOutput)

    @agent
    def qa_agent(self) -> Agent:
        return Agent(
            role="qa_agent",
            backstory="You are a question-answering agent. You help people find answers to their questions.",
            goal="Provide accurate and concise answers to the questions asked.",
        )

    @agent
    def fun_fact_agent(self) -> Agent:
        return Agent(
            role="fun_fact_agent",
            backstory="You are a fun fact agent. You provide interesting and fun facts on various topics.",
            goal="Provide a fun fact related to the topic of the question.",
        )

    @task
    def qa_task(self) -> Task:
        return Task(
            name="qa_task",
            agent=self.qa_agent(),
            description="Provide accurate and concise answers to the questions asked.",
            expected_output="A concise and accurate answer to the question.",
        )

    @task
    def fun_fact_task(self) -> Task:
        return Task(
            name="fun_fact_task",
            agent=self.fun_fact_agent(),
            description="Provide a fun fact related to the topic of the question.",
            expected_output="A fun fact related to the topic of the question.",
        )

    @agent
    def manager(self) -> Agent:
        return Agent(
            role="manager",
            backstory="You are the manager of the multi-tool crew. Your crew is highly skilled, capable of answering questions and handling tasks. You coordinate the agents and tasks to provide the best possible response to the user's question.",
            goal="Coordinate the agents and tasks to provide the best possible response to the user's question.",
            allow_delegation=True,
        )

    @crew
    def trip_plan_crew(self):
        return Crew(
            name="trip_plan_crew",
            agents=[self.location_agent(), self.weather_agent()],
            tasks=[self.location_task(), self.weather_forecast(), self.clothing_recommendation()],
            process=Process.sequential,
        )
