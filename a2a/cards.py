"""
a2a/cards.py
═══════════════════════════════════════════════════════════════════════════════
A2A Agent Cards and metadata definitions for all specialist agents.
═══════════════════════════════════════════════════════════════════════════════
"""

from a2a.types import AgentCard, AgentCapabilities, AgentSkill

STUDY_AGENT_CARD = AgentCard(
    name="Student Study Agent",
    description="Handles academic learning, topic explanations, summaries, and quiz generation.",
    url="http://127.0.0.1:9001/",
    version="2.0.0",
    default_input_modes=["text"],
    default_output_modes=["text"],
    capabilities=AgentCapabilities(streaming=True),
    skills=[
        AgentSkill(
            id="explain_topic",
            name="explain_topic",
            description="Explains an academic topic at a specified depth level (beginner, intermediate, advanced).",
            tags=["study", "explanation", "academic"],
        ),
        AgentSkill(
            id="generate_quiz",
            name="generate_quiz",
            description="Generates multiple-choice quiz questions to test knowledge on any subject.",
            tags=["study", "quiz", "test"],
        ),
    ],
)

SCHEDULE_AGENT_CARD = AgentCard(
    name="Student Schedule Agent",
    description="Manages study tasks, assignments, deadlines, and schedule viewing.",
    url="http://127.0.0.1:9002/",
    version="2.0.0",
    default_input_modes=["text"],
    default_output_modes=["text"],
    capabilities=AgentCapabilities(streaming=True),
    skills=[
        AgentSkill(
            id="add_task",
            name="add_task",
            description="Adds a new task, assignment, or study session to the schedule.",
            tags=["schedule", "task", "plan"],
        ),
        AgentSkill(
            id="view_schedule",
            name="view_schedule",
            description="Retrieves and displays scheduled tasks, optionally filtered by subject.",
            tags=["schedule", "view", "tasks"],
        ),
    ],
)

RESEARCH_AGENT_CARD = AgentCard(
    name="Student Research Agent",
    description="Performs web research, searches the web, and extracts information from online sources.",
    url="http://127.0.0.1:9003/",
    version="2.0.0",
    default_input_modes=["text"],
    default_output_modes=["text"],
    capabilities=AgentCapabilities(streaming=True),
    skills=[
        AgentSkill(
            id="search_web",
            name="search_web",
            description="Searches the web for up-to-date articles, documentation, or tutorials.",
            tags=["research", "search", "web"],
        ),
        AgentSkill(
            id="scrape_webpage",
            name="scrape_webpage",
            description="Retrieves webpage content from a URL.",
            tags=["research", "scrape", "web"],
        ),
        AgentSkill(
            id="extract_page_content",
            name="extract_page_content",
            description="Extracts clean readable text and article content from a web page.",
            tags=["research", "extract", "content"],
        ),
    ],
)

AGENT_CARDS = {
    "study": STUDY_AGENT_CARD,
    "schedule": SCHEDULE_AGENT_CARD,
    "research": RESEARCH_AGENT_CARD,
}
