"""用户模块用例：注册/登录/鉴权。

设计思路——按"等价类"划分输入域再取代表值：
- 用户名: 合法(3-32) / 边界(3, 32) / 非法(2, 33, 空)
- 密码:   合法(6-64) / 边界(6, 64) / 非法(5, 65)
- 登录:   正确 / 密码错 / 用户不存在 / token 伪造 / token 缺失
"""


def test_register_success(auth_api):
    resp = auth_api.register()
    assert resp.status_code == 201
    body = resp.json()
    assert "id" in body and "username" in body
    # 安全断言：响应绝不能泄露密码哈希
    assert "password_hash" not in body


def test_register_duplicate_username(auth_api):
    resp = auth_api.register(username="dup_user_001", password="pass123456")
    assert resp.status_code == 201
    resp2 = auth_api.register(username="dup_user_001", password="other99999")
    assert resp2.status_code == 400


def test_register_username_too_short(auth_api):
    assert auth_api.register(username="ab", password="pass123456").status_code == 422


def test_register_username_too_long(auth_api):
    assert auth_api.register(username="x" * 33, password="pass123456").status_code == 422


def test_register_password_too_short(auth_api):
    assert auth_api.register(username="validname", password="12345").status_code == 422


def test_register_boundary_values(auth_api):
    """边界值分析：3/32 位用户名、6/64 位密码都是合法边界，应全部 201。"""
    assert auth_api.register(username="abc", password="123456").status_code == 201
    assert auth_api.register(username="y" * 32, password="p" * 64).status_code == 201


def test_login_success(user, auth_api):
    username, password = user
    resp = auth_api.login(username, password)
    assert resp.status_code == 200
    token = resp.json()["access_token"]
    # JWT 结构断言：三段式 header.payload.signature
    assert token.count(".") == 2


def test_login_wrong_password(auth_api):
    auth_api.register(username="login_test_1", password="right_pass")
    resp = auth_api.login("login_test_1", "wrong_pass")
    assert resp.status_code == 401


def test_login_nonexistent_user(auth_api):
    assert auth_api.login("no_such_user_xyz", "whatever1").status_code == 401


def test_login_error_message_no_user_enumeration(auth_api):
    """安全用例：'密码错'与'用户不存在'的报错必须一致，防用户名枚举。"""
    auth_api.register(username="enum_test_1", password="right_pass")
    _, r1 = auth_api.login("enum_test_1", "wrong_pass").status_code, None
    r1 = auth_api.login("enum_test_1", "wrong_pass")
    r2 = auth_api.login("enum_test_2", "wrong_pass")
    assert r1.json()["detail"] == r2.json()["detail"]


def test_me_requires_token(auth_api):
    assert auth_api.me().status_code == 401


def test_me_with_forged_token(auth_api, client):
    """伪造签名的 token 必须被拒（HS256 密钥校验）。"""
    client.set_token("eyJhbGciOiJIUzI1NiJ9.fake.fake")
    assert auth_api.me().status_code == 401


def test_me_success(user, auth_api):
    resp = auth_api.me()
    assert resp.status_code == 200
    assert "username" in resp.json()
