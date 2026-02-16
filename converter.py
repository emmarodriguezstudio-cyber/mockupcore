import base64

# This looks for your font file and turns it into text
with open("SpaceGrotesk-Regular.ttf", "rb") as f:
    text_version = base64.b64encode(f.read()).decode('utf-8')
    
# This creates a new file for you called 'my_font.txt'
with open("my_font.txt", "w") as f:
    f.write(text_version)

print("Done! Open 'my_font.txt' and copy everything inside.")