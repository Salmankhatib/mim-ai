    ** Main TODO : These have to be done before general release **

1. Make sure the Normlizer works and is simple + does not turnicate.

2. Make sure logs are ok, audit + normlizer logs.
        - 1. Configurable configuration to a specific db.
        - 2. If not a sql db as backup.

3. Refactor the STT, TSS and the pipline (STT - LLM - TSS).
        - 1. Configurable via the main config. (normlize or not, intent or not).
        - 2. the pipline must have tools and configurable parms.
        - 3. The methods listen, speak and Listen and speak (The full pipline).
Main idea : Three methods, one config, zero bloat.

4. Test every single method under many patnerns.

5. No LLM Router : all LLM router related code should be deleted. (We are no longer doing this).

    ** Documentation TODO : These have to be done before general release **

    1. Write a clear sellable README.md (The benefits have to be clear)
    2. Write a tutorial.md
    3. Write architecture.md
    4. Write a contribution.md
    5. Write a doc about each feature how it works, why (the benefits of it), how to config and use in code. with clear exemple.
    6. create a fastAPI that uses all the features. (In a seperated file called project exemple).
    7. Maybe write a Manifesto.md (Basicly why this project, how it aligns with gov view etc..)

Note : The docs must be in EN, FR. (Have separated files).