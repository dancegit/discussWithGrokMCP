# Records docs/demo-panel.gif: three agents debate a topic, then the moderator recommends.
# Needs vhs (https://github.com/charmbracelet/vhs) and either XAI_API_KEY in .env or a
# signed-in grok CLI (GROK_BACKEND=cli). Then shorten the waits:
#   vhs docs/demo-panel.tape
#   uv run --with pillow python scripts/squash_gif.py docs/demo-panel.gif docs/demo-panel.gif 1500 8000
Output docs/demo-panel.gif

Set Shell "bash"
Set FontSize 15
Set Width 1100
Set Height 760
Set Padding 18
Set Theme "Catppuccin Mocha"
Set TypingSpeed 45ms

Hide
Type "export PS1='$ ' && clear"
Enter
Show

Type "uv run python scripts/demo_panel.py"
Sleep 400ms
Enter
Wait@300s /^\$$/
Sleep 4s
