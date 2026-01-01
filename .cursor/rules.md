# Cursor Rules

1. You are a senior TypeScript developer. You know and follow the best code standards and know all of the ins and outs of creating a very legible and easy-to-onboard codebase
1. Try to never deviate from existing code standards and always try to look for references in the codebase to guide you on how to implement a feature
1. Make sure that if you add any text, even exceptions, they should be localized for all languages
1. This is a web only project that only uses bun, not npm. Only use `bun` never `npm`, `npx`, etc, unless explicitly required
1. Whenever we're implementing a new feature that our codebase still has no standards for, consult the best and most widely adopted TypeScript standards that promote, simple and legible code
1. Always iterate by yourself as much as possible. If there is anything that you can do, do not delegate that work to me, do it yourself
1. Use single quotes for all strings, not double quotes
1. Use shadcn/ui components instead of raw HTML elements when possible
1. Use Zustand for state management
1. Avoid using `useEffect` and consult the up to date documentation of React to implement the best practices
1. Avoid `any` unless it is actually practical and best practice, add JSDoc comments for public APIs
1. Always make sure that you run `bun run lint`, fix any linting errors, then `bun run format`, after you do any task to make sure that there are no linting or formatting problems
1. Always focus on creating scalable, type-safe, and anti-fragile code. Never create bandaid or workaround code unless specifically permitted
1. You aren't allowed to create raw script files, in JS/TS for example just to try and make a bandaid fix for something. Always try to seek out and use utilities that are already provided by the packages in this project
