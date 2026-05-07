1. 跨端通信网关与路由规范 (Routing & Gateway)

前缀防线：所有发往 STM32 本地外设（如 DRV SPI 控制）的原始指令，必须在封包时强制打上 STM: 路由标签（如 STM:MAOM 0 0200），否则会被 STM32 底层状态机的协议防火墙拦截丢弃。

2. 异步通信与时序防爆 (Async & Race Condition Defense)

QEventLoop 同步阻塞：在 PyQt5 子界面中，严禁使用 time.sleep() 或空 while 循环等待串口返回。必须利用 QEventLoop 配合 QTimer 实现“代码阻塞但 UI 不卡死”的同步读取。

读写指令分离与握手确认：

对于连续的 Write -> Read 操作（如 Vendor R 的 020D 寻址后读 020E），写指令必须同样进入 QEventLoop 阻塞，等待底层回复 ACK:WRITE 后再释放。

绝对禁止“发完即走”的写操作，否则会导致极速下发的读指令错误截获写指令的 ACK 包，造成数据“张冠李戴”。

精准拦截器 (Interceptor)：总线数据回填时，不仅要识别 0x，必须强校验包头的 READ 或 WRITE 属性，实施物理分流。

3. UX 与状态机安全 (UX & Dirty Data Isolation)

前置硬件锁：子界面（如 DRV 模块）操作前，需同步检查主控制器的 is_serial_connected 状态。断网时直接 UI 弹窗阻断，杜绝无意义的底层超时死等。

阅后即焚 (Reset on Close)：子界面的 closeEvent 必须挂载彻底清空历史日志、文本框数据和厂家锁定标志（Flag）的清理函数，消灭脏数据 (Dirty Data) 污染下一次测试的风险。
