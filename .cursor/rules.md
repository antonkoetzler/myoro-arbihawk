# Cursor Rules

1. Try to never deviate from existing code standards and always try to look for references in the codebase to guide you on how to implement a feature

2. Make sure that if you add any text, even exceptions, they should be localized for all languages

3. This is a web only project that only uses bun, not npm

4. Whenever we're implement a new feature that our codebase still has no standards for, consult the best and most widely adopted TypeScript standards that promote, simple and legible code

5. Always iterate by yourself as much as possible. If there is anything that you can do, do not delegate that work to me, do it yourself

6. Use single quotes for all strings, not double quotes

7. Use shadcn/ui components instead of raw HTML elements when possible

8. Use Zustand for state management, not React `useState` for complex state

9. All user-facing text must be added to the i18n system with translations for all supported languages

10. Follow TypeScript best practices: use proper types, avoid `any` unless it is actually practical and best practice, add JSDoc comments for public APIs

11. Always make sure that you run `bun run lint`, fix any linting errors, then `bun run format`, after you do any task to make sure that there are no linting or formatting problems

12. Always focus on creating scalable, type-safe, and anti-fragile code. Never create bandaid or workaround code unless specifically permitted
