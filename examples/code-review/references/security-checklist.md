# 安全审查详细清单

## 1. 注入类漏洞

### SQL 注入

```python
# ❌ 危险
query = f"SELECT * FROM users WHERE id = {user_id}"

# ✅ 安全
query = "SELECT * FROM users WHERE id = %s"
cursor.execute(query, (user_id,))
```

### 命令注入

```python
# ❌ 危险
os.system(f"convert {user_input} output.png")

# ✅ 安全
subprocess.run(["convert", user_input, "output.png"], check=True)
```

### 路径遍历

```python
# ❌ 危险
filename = request.GET["file"]
return open(f"/uploads/{filename}").read()

# ✅ 安全
filename = secure_filename(request.GET["file"])
full_path = os.path.join("/uploads", filename)
full_path = os.path.realpath(full_path)
if not full_path.startswith("/uploads"):
    abort(403)
```

## 2. 敏感数据

```python
# ❌ 危险
API_KEY = "sk-1234567890abcdef"

# ✅ 安全
API_KEY = os.environ["API_KEY"]
```

## 3. 加密 & 认证

- 密码必须 bcrypt / argon2 哈希
- Token 不能放 URL（应在 Authorization header）
- 不用自创加密算法
- HTTPS 强制

## 4. 错误处理

```python
# ❌ 错误：吞掉异常
try:
    do_something()
except:
    pass

# ❌ 错误：泄露内部细节
except Exception as e:
    return f"Error: {traceback.format_exc()}", 500

# ✅ 正确
except SpecificException as e:
    logger.exception("operation failed")
    return "Internal error", 500
```

## 5. 反序列化

```python
# ❌ 危险：pickle 反序列化不可信数据
data = pickle.loads(request.data)

# ✅ 安全：用 JSON
data = json.loads(request.data)
```

## 6. XSS

```javascript
// ❌ 危险
element.innerHTML = userInput;

// ✅ 安全
element.textContent = userInput;
```

## 7. SSRF

```python
# ❌ 危险
url = request.json["url"]
return requests.get(url).text

# ✅ 安全
from urllib.parse import urlparse
url = request.json["url"]
parsed = urlparse(url)
if parsed.hostname in ALLOWED_HOSTS:
    return requests.get(url).text
```

## 自检清单

- [ ] 没有硬编码 secret
- [ ] 没有 SQL 字符串拼接
- [ ] 没有 os.system(user_input)
- [ ] 文件路径已校验
- [ ] 密码用 bcrypt
- [ ] 异常不泄露内部细节
- [ ] 没有 pickle 反序列化
- [ ] 没有 innerHTML 拼接
- [ ] SSRF 域名已白名单
