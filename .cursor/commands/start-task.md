# /start-task

This command should be used at a stage in a chat where a feature has already been chosen and is ready to be discussed

Before doing anything, please confirm with me what the task we're implementing is. I'll either provide the topic, or you'll just infer what task I'm talking about. If you infer the task, you must say this, `You will want to implement <TASK>, right? Proceed?`. I must give you an approval of the task, to make sure you've infered the right one before you continue with anything. Do not start coding yet, at this point, either when I've given you a task, or you've correctly infered the task, you will then give me a mini-lecture (keep it short) of the description of the task, what the task is, and a brief of how you'll edit the code to complete this task. After this mini-lecture, at the end of the prompt, you will say `Proceed?`. If I say yes (or any positive approval, i.e. not no/stop/etc), you can move onto the bottom part of this task, the planning/implementation stage, if I give a disapproval, just don't continue, stop.

## Planning/Implementation Stage

### First step: Interrogation

Once you've arrived at this point of the command, you will then ask me any questions/concerns/suggestions you have. You will repeatedly do this, however many times as you need, until you are very confident that you can implement this task. Once you're very confident, you can move onto the next step.

### Third step: Pillars to focus on when implementing the task

> If the chat is in plan mode, you must add all of this to the plan, doesn't have to be verbatim.
> Also, if the chat is in plan mode, do not use Cursor's integrated plan question flow, it sucks

1. Make sure to follow `.cursor/rules`
2. Make sure to own the entire development lifecycle: Implement, test, debug, repeat. Be thorough and keep iterating until you think the feature is perfect and good to go
3. Document all new functionality being added. Don't be overly specific and don't deviate from writing standards
4. Make sure you implement functionality for every part of the codebase. Strive to make the user not have to touch code or run commands at all, so here are the main pillars of functionality:

- Python code (obviously)
- Dashboard frontend features + integrated with dashboard backend if needed
- VSCode tasks (idk if this feature itself will be applicable, but you get the point
