# SpringBoot

[[backend/backend|返回上级：backend]] · [[main|返回知识主干]]

Spring Boot 应用结构、依赖注入、配置与 Web 开发。

# Spring Boot 入门：MVC、Bean、IoC / DI 与构造器注入

## 一、核心概念映射（Python / 工程视角）

| Spring 概念 | 本质定义 | 工程直觉类比 |
| :--- | :--- | :--- |
| **Spring 容器（ApplicationContext）** | 应用启动时运行的全局对象工厂与注册表 | 启动入口维护的全局 `registry = {}` 对象字典 |
| **Bean** | 由 Spring 容器创建并管理生命周期的普通 Java 对象实例（默认单例） | 存放在 `registry` 中的具体服务实例 |
| **控制反转（IoC, Inversion of Control）** | 对象创建权从业务代码上交给框架，不再手动到处 `new` | 交给框架启动生命周期统一初始化依赖 |
| **依赖注入（DI, Dependency Injection）** | 类只声明所需依赖，框架在启动装配时自动传入对应 Bean | 类似 FastAPI 的 `Depends(...)` 或通过 `__init__` 注入实例 |

## 二、为什么不写 `new` 服务也能跑：完整执行链路

程序并非没有 `new` 对象，而是由 Spring 在**启动期通过 Java 反射（Reflection）**统一完成实例化与装配，并在**运行期复用单例 Bean**：

1. **入口扫描**：运行 `mvn spring-boot:run` 后，主启动类上的 `@SpringBootApplication`（内含 `@ComponentScan`）从主包向下扫描所有类文件。
2. **登记图纸**：发现带 `@Service`、`@RestController` 等注解的类，先将其元信息封装为 `BeanDefinition` 登记进容器。
3. **反射建对象**：容器按依赖顺序，先通过反射创建无依赖或底层依赖的 Bean（如 `GreetingService`），放入单例缓存池（本质为线程安全的 `ConcurrentHashMap`）。
4. **构造器装配**：创建 `HelloController` / `EventController` 时，容器发现其唯一构造器需要对应的 Service 参数（Spring 4.3+ 单构造器可省略 `@Autowired`），从单例池按类型取出 Bean 自动注入，并将接口路径注册进路由表（`HandlerMapping`）。
5. **运行期复用**：内嵌 Tomcat 监听 `8080` 端口；收到 HTTP 请求后，`DispatcherServlet` 查路由表直接复用启动期已建好的单例 Controller 与 Service，内置 Jackson 自动将返回对象序列化为 JSON。

### 为什么优先使用构造器注入（而非字段 `@Autowired`）

- **支持 `final` 不可变**：依赖在构造完成后锁定，避免运行期被意外修改或出现空指针。
- **依赖显式透明**：构造器参数列表即依赖清单，依赖过多时能第一时间暴露职责膨胀。
- **单元测试友好**：写单测时无需启动 Spring 容器，直接 `new Controller(mockService)` 即可完成测试。

## 三、常用 Web 与分层注解速查

| 注解 | 位置 | 作用说明 |
| :--- | :--- | :--- |
| `@RestController` | Controller 类 | 等价于 `@Controller + @ResponseBody`：注册为处理 HTTP 请求的 Bean，且方法返回值直接序列化为 JSON 写入响应体 |
| `@RequestMapping("/api")` | Controller 类 | 为整个类设置统一 URL 路径前缀 |
| `@GetMapping("/{id}")` | Controller 方法 | 限定仅接收 HTTP `GET` 请求，并将路径拼接在类前缀之后 |
| `@RequestParam` | 方法参数 | 提取 URL 查询参数（如 `/api/hello?name=Java`），默认必填（`required = true`），可配 `defaultValue` |
| `@PathVariable` | 方法参数 | 提取 URL 路径占位符（如 `/api/events/1` 中的 `1`），并自动完成类型转换（如转成 `Long`） |
| `@Service` | Service 类 | `@Component` 的语义化派生注解：框架层面注册为 Bean 托管，架构层面标明属于业务逻辑层 |

## 四、实战代码骨架（内存版分层）

- **数据模型（`model/Event.java`）**：使用 Java 21 `record` 定义不可变实体，ID 使用包装类型 `Long`：
  ```java
  public record Event(Long id, String title, String location, int capacity) {}
  ```
- **业务层（`service/EventService.java`）**：加 `@Service`，暂用内存 `List<Event>` 保存模拟数据，查不到时抛出 `ResponseStatusException(HttpStatus.NOT_FOUND, ...)` 返回标准 `404`。
- **控制层（`controller/EventController.java`）**：通过构造器注入 `EventService`，仅负责接收 `@PathVariable Long id` 并调用 `eventService.findById(id)`，不直接操作数据。

## 五、当日实战踩坑与排错记录

1. **Maven 插件命令拼写错误**：将 `mvn spring-boot:run` 误输为 `mvn sprint-boot:run`，触发 `NoPluginFoundForPrefixException`（代码本身未进入编译阶段）。
2. **`long` 与 `Long` 混用导致编译报错（`无法取消引用long`）**：`Event` 中将 `id` 写成基本类型 `long`，而在 `EventService` 中调用了 `event.id().equals(id)`。基本类型不是对象，无法调用方法；后端实体 ID 统一使用包装类型 `Long`（也兼容入库前 `id` 为 `null` 的场景）。
3. **路径参数与查询参数混用导致 `404`**：对 `@GetMapping("/{id}")` 接口发送 `GET /api/events?id=1`，Spring 匹配路由时只看 `/api/events` 导致找不到路径；正确请求应为 `GET /api/events/1`。
4. **缺少 `@Service` 的报错特征**：注释 `@Service` 后启动会抛出 Bean 缺失错误（`required a bean of type '...' that could not be found`），这是排查注入失败的首要线索。

## 六、个人验收复盘（Day 4 五题核对）

1. **`@RestController` 的作用**：不仅是让 Spring 托管 REST Controller，关键在于它是 `@Controller + @ResponseBody` 的组合，负责把方法返回值直接转成 JSON 写进响应体。
2. **`@GetMapping("/{id}")` 与 `@PathVariable` 的配合**：限定 GET 方法、拼接在类级 `@RequestMapping` 后，并把路径占位符的值提取、类型转换后绑定给 `@PathVariable` 参数。
3. **`@Service` 的作用**：语义上标明业务逻辑层；框架层面让 Spring 扫描并托管为单例 Bean（无论该 Service 是否有其他下层依赖，容器都会按依赖顺序自动装配）。
4. **`EventService` 由谁创建**：由 Spring IoC 容器（`ApplicationContext`）在启动时通过反射创建并托管，再通过 DI 注入给 `EventController`（避免笼统表述为“注入到 JVM 创建”）。
5. **Controller 与 Service 为什么要分层**：职责清晰（Controller 管 HTTP 协议与路由，Service 管业务逻辑与编排）、隔离数据层变化（Day 5 换 MyBatis + MySQL 时 Controller 无需改动）、便于多 Controller 复用、利于独立单元测试及后续在 Service 层统一加事务控制（`@Transactional`）。

