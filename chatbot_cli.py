"""Simple REPL for the Minnesota election chatbot."""

from __future__ import annotations

from chatbot import ElectionChatbot


def main() -> None:
    bot = ElectionChatbot()
    print("Minnesota Election Chatbot. Ask for data (e.g. '2024 president results in Hennepin County').")
    print("Type 'quit' to exit.\n")
    while True:
        try:
            message = input("You: ")
        except EOFError:
            break

        if not message:
            continue

        if message.lower().strip() in {"quit", "exit"}:
            break

        print(f"Bot: {bot.reply(message)}\n")


if __name__ == "__main__":
    main()
