from PIL import Image
img=Image.open('assets/ey_logo.png').convert('RGBA')
# shrink if too big
max_dim = 512
scale = min(max_dim/img.width, max_dim/img.height, 1)
if scale < 1:
    img = img.resize((int(img.width*scale), int(img.height*scale)), Image.LANCZOS)
size=max(img.size)
canvas=Image.new('RGBA',(size,size),(255,255,255,0))
canvas.paste(img,((size-img.width)//2,(size-img.height)//2),img)
sizes=[(16,16),(24,24),(32,32),(48,48),(64,64),(128,128),(256,256)]
canvas.save('assets/ey_logo.ico', sizes=sizes)