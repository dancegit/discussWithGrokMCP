# Records docs/demo.gif. Needs vhs (https://github.com/charmbracelet/vhs) and XAI_API_KEY in .env.
#   vhs docs/demo.tape
Output docs/demo.gif

Set Shell "bash"
Set FontSize 15
Set Width 1100
Set Height 640
Set Padding 18
Set Theme "Catppuccin Mocha"
Set TypingSpeed 45ms

Hide
Type "export PS1='$ ' && clear"
Enter
Show

Type "uv run python scripts/demo.py"
Sleep 400ms
Enter
Wait@120s /^\$$/
Sleep 4s
