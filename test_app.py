import pytest
from fastapi.testclient import TestClient
from app import app  # 导入 FastAPI 应用

# 创建测试客户端
client = TestClient(app)


# 测试图像生成
def test_generate_image():
    # 直接调用 FastAPI 路由进行测试，传入真实的参数
    response = client.get(
        "/",
        params={
            "cover":
            "https://raw.githubusercontent.com/cnrenil/music-image-generate/main/cover.jpg",
            "title": "Test Title",
            "artist": "Test Artist"
        })

    # 检查响应状态码和内容类型
    assert response.status_code == 200
    assert response.headers["content-type"] == "image/png"
    # 可以在这里添加进一步的断言以验证生成的图像内容


# 运行所有测试
if __name__ == "__main__":
    pytest.main()
