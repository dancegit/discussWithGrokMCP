# Records docs/demo-discussion.gif: a discussion resumed after a server restart.
# Needs vhs (https://github.com/charmbracelet/vhs) and either XAI_API_KEY in .env or a
# signed-in grok CLI (GROK_BACKEND=cli). Then shorten the waits:
#   vhs docs/demo-discussion.tape
#   uv run --with pillow python scripts/squash_gif.py docs/demo-discussion.gif docs/demo-discussion.gif 1500 8000
Output docs/demo-discussion.gif

Set Shell "bash"
Set FontSize 15
Set Width 1100
Set Height 720
Set Padding 18
Set Theme "Catppuccin Mocha"
Set TypingSpeed 45ms

Hide
Type "export PS1='$ ' && clear"
Enter
Show

Type "uv run python scripts/demo_discussion.py"
Sleep 400ms
Enter
Wait@120s /^\$$/
Sleep 4s
