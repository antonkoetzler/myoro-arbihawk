# /work-backlog

1. Open `./src/arbihawk/docs/backlog.md`
2. Study the codebase, and see if there are any tasks that should be REMOVED from or ADDED to `./src/arbihawk/docs/backlog.md`

- This is moreso just a sanity check because I had you, AI, make this backlog
- Please make sure that you remember to only remove tasks if it will not improve profitability in the application
- Please make sure that you remember to only add tasks if it will (objectively, with evidence backing it preferably) improve profitability in the application
- Don't add or remove things just because you feel like you have to "complete" this step, it's completely normal to leave this step if you don't find anything

3. Read `./src/arbihawk/docs/backlog.md` and find the best and most high priority task(s) that should be done right now

- Make sure you only tackle a more complex and higher priority task if it most rationale to do before completing other tasks
- You are encouraged to implement various tasks at once if they are related to eachother and should/can be done in tandem

4. You're going to tell which task(s) you've done, give me a brief rundown of what will need to be changed
5. If you have any questions regarding the task, you'll ask me before you get started
6. After you've asked me ALL of your questions, concerns, suggestions, doubts, etc, you'll ask me if we should proceed. YOU CANNOT CODE UNLESS I GIVE YOU THE APPROVAL TO START
7. If I say you can proceed, you will the implement the task from start to finish

- Make sure you obey all rules in `.cursor/rules`
- You are the code owner, you ultimately make the best decisions for all code related matters
- You own the development lifecycle, you implement, test, debug, and repeat until all code is working perfectly
- You must make sure everything has provided functionality, so for example:
  - If it's a feature that could be added to `.vscode/tasks.json`, make sure there is a task for it
  - If it's a feature that can be used in the arbihawk dashboard frontend, add it to the front and backend
  - Make sure all Pyhton code has provided functionality
  - Do not leave residual files hanging around, if you want to keep any files to reuse later, in a different chat add them to `.cursor/scripts`

8. After you've completed the task(s), you will remove the task(s) from `./src/arbihawk/docs/backlog.md` completely—do NOT leave them in an "implemented" or "Recently Completed" state, and do NOT re-add completed tasks to the backlog in any form
