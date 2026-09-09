# 作者整理的来源笔记

学习者已经知道一次 HTTP 请求会收到响应。本课不重讲请求与响应，只解决评审缓存配置时的一个新判断。

RFC 9111 把缓存中的响应区分为 fresh 和 stale。fresh 响应通常可以直接复用；stale 响应通常不能在没有验证或其他明确许可的情况下直接生成响应。RFC 还介绍了 Date、Age、max-age、Expires、ETag 和 Last-Modified 等字段。

MDN 文档说，重新验证时客户端或缓存可以携带 If-None-Match 或 If-Modified-Since。如果资源没有变化，源站可以返回 304 Not Modified，复用已有响应体。

两份材料都真实，用途不同。RFC 讲规范要求，MDN 讲开发者怎样理解。本课只需要知道它们可以互相对照。
