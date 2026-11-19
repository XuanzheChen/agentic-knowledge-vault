# REST API

[[backend/backend|返回上级：backend]] · [[main|返回知识主干]]

REST 风格接口设计、资源与路径、请求方法和状态码。

## 问题目录

- [[backend/REST API/REST API#什么是 REST API？|什么是 REST API？]]

---

## 什么是 REST API？

**REST API 是遵循 REST（Representational State Transfer，表述性状态转移）架构风格设计的应用程序接口。在常见的 Web 后端开发中，可以将它理解为：基于 HTTP 协议，按照一套资源导向的架构原则来设计接口。**

理解 REST API，首先要区分 **HTTP 协议** 和 **REST 架构风格**：

- **HTTP 是通信协议**：规定客户端与服务器如何发送请求、返回响应，例如请求方法（`GET`、`POST`）、URL、请求头、响应体和状态码（`200`、`404` 等）。
- **REST 是接口设计的架构风格**：并不另造一套传输协议，而是在 Web 场景中利用 HTTP 已有的机制，约束开发者**如何组织资源、设计请求以及表达操作结果**。因此 REST 不是 HTTP 本身，也不是必须强制遵守的单一接口标准；并非所有 HTTP API 都属于 REST API。

REST 风格的 HTTP API 通常有以下特点：

1. **以资源为中心**：用 URI 定位资源，例如 `/users/123` 表示编号为 123 的用户；接口路径通常使用名词描述资源，而非把每个动作写成路径。
2. **利用 HTTP 方法表达操作意图**：常见约定为 `GET` 查询、`POST` 创建、`PUT` 整体更新、`PATCH` 部分更新、`DELETE` 删除。具体行为仍需遵守各方法的 HTTP 语义。
3. **利用 HTTP 状态码反馈结果**：例如 `200 OK` 表示请求成功，`201 Created` 表示创建成功，`404 Not Found` 表示未找到资源。
4. **无状态（Stateless）**：每个请求都应携带服务器处理它所需的信息，服务器不依赖之前请求保存的客户端会话上下文；这不等于服务器不能存储数据库中的业务状态。
5. **使用资源的表述交换数据**：客户端和服务器经常通过 JSON 传递资源信息，也可以使用 XML 等格式；REST 本身并不要求必须使用 JSON。

以用户管理为例：

| HTTP 请求 | 含义 |
| --- | --- |
| `GET /users/123` | 获取编号为 123 的用户 |
| `POST /users` | 创建用户 |
| `PUT /users/123` | 整体更新该用户 |
| `DELETE /users/123` | 删除该用户 |

所以，**HTTP 解决“请求与响应怎样传输和表达”，REST 解决“如何合理设计围绕资源的 Web API”**。可以把常见的 REST API 看作在 HTTP 之上采用 REST 架构风格的接口，但从严格概念上说，REST 是架构风格而非只能用于 HTTP 的专有协议。

参考：[菜鸟教程：REST API 教程](https://www.runoob.com/w3cnote/rest-api-tutorial.html)。
