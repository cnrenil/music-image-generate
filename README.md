# music-image-generate

音乐图片生成

# 使用
`pip install -r requirements.txt`和`playwright install firefox`
GET传入参数：title标题，artist作者，cover封面链接，lyrics歌词链接即可
如果你有Docker，可以直接`docker compose up -d`自动构建并运行，端口在3006
# 修改字体
编辑`app.py`内部的字体设置即可，记得修改模板HTML的字体为相应字体族

# 预览

![1000498757.png](https://img.renil.cc/i/2024/07/29/66a6f0bcbaf5c.png)
![1000498758.png](https://img.renil.cc/i/2024/07/29/66a6f0bd613a8.png)

# 原理

Chat GPT原理🤣

先生成一个好看点的模板，然后生成一个Python，把HTML截图就好了。composer install和npm install一下，放在环境里面就可以跑，不推荐放在公网环境下

# 协议/LICENSE

MIT
