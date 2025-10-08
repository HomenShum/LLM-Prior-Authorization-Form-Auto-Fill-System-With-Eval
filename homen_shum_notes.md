# Actions

1. Understanding
    1. From 1:30PM to 5PM, implement the /answer api endpoint with LLM to ingest 
        1. Input: 
            1. Patient Info 
            2. Clinical Note 
            3. Question from the Prior Authorization Form
            4. Human Feedback
        2. Output: 
            1. Answer
            2. Rationale
        3. Additionally: 
            1. Upload Files Input Field
            2. Human Feedback Input Field
            3. AI Rationale Output Field
            4. Eval Pipeline
            5. Streaming Output
            6. Cache Response 
            7. Optimizations: 
                1. Actor-critic system
                2. Reasoning models
                3. Few shot prompts
2. Prototyping
    1. Let’s generate a self-contained HTML given the project description to visualize our UI UX Flow first.
        1. Screenshot + URL
    2. Let’s choose the frontend implementation stack
        1. Python Streamlit is easy (AI Engineer Route)
        2. Typescript React Convex is pretty (Product Route)
    3. Push commits to a new branch as you go.
3. Live session to discuss the project in more detail. Answering why a certain piece is implemented a particular way
    1. Go deeper into a few of the extra pieces and come with novel insights and tech challenges to discuss in the live session
    2. Evaluation Criteria:
        - Functionality: Does the application work as described in the instructions?
        - Code Quality: Is the code easy to understand and maintain? Is it organized well? We're an early stage startup so plenty of times it's the right call to go with a 'hacky' solution that gets the job done quickly. What is important is to consciously choose these cases and document them well (which can be just a comment in the code).
        - Testing: Are there adequate tests for the application? We don't expect (or want) you to write unit tests for everything. But an integration test or two is normally a good idea. If you don't have time to include these you can just outline what you would test in your write-up.
        - Documentation: Is the application and its design well-documented?
        - Design Write-Up: Do you clearly explain your design choices, assumptions, and tradeoffs?
        - Innovative Design: Does the implementation demonstrate creative or thoughtful design decisions?
    3. Deliverables
        1. A FastAPI application in Python that implements the `/answers` endpoint as described above.
        2. A PR with the following description:
            - Overview of what you implemented and how
            - Design choices, assumptions, and tradeoffs
            - How you used AI tools in completing this project. See below for more details
        3. A short (~5 min) loom (or similar video walkthrough) showing what you built and brief overview of the code. Please demonstrate the frontend if you chose to build one (not required).
        4. Discussions:
            - How did you prompt the LLM to get good results?
            - What worked and didn't work if you tried to first vibe code this whole project?
            - Is there a new tool you've come across that works better than others? Teach us all about it!