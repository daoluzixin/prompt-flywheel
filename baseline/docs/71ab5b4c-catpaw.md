🙋 Round 1  2026-05-07 15:21:25
用户：你看下这里plan解析note的时候，我发现经常会出现不明的跳格啊 比如这种： [历史实例]: 企客校园送业务线标识写入 PR wcw#62 参照 CompatiblePackageHelp.java:341: 已有extMap.put("serviceSpuCode", ...)同类模式 新增逻辑在serviceSpuCode写入后追加: 若bizCode非空则extMap.put("bizCode", bizCode) 同时从poiAggre JSON解析companyCustomerId写入extMap.put("companyCustomerId", ...) 就经常跳格***
AI：我先看一下 `parse` 目录里关于 plan 解析 note 的脚本，定位"跳格"问题的根源

🙋 Round 2  2026-05-07 15:54:18
用户：像类似于[基线对照] 这种 括号包裹的，或者英文都可以搞特殊的背景进行渲染，这样更明显一点
AI：我在 `_renderNote` 里再加两条高亮规则：`[xxx]` / `【xxx】`（中英文方括号包裹）做语义徽标；纯英文短语（连续英文单词）做淡背景高亮

🙋 Round 3  2026-05-07 15:58:46
用户：我觉得样式不好看，你看你那个不是有大写英文字母后面跟着.方法的就会渲染成紫色啥的吗，我觉得英文都可以按照这个进行渲染
AI：你想让所有英文（不只是 `ClassName.method()`）都用 `.note-code` 那种紫色 + 灰底 + 等宽的样式
