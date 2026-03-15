/**
 * Monitoring Layout
 *
 * 监控页面的根布局
 */

export const metadata = {
  title: 'Agent 监控中心',
  description: '实时监控智能体执行过程、状态和性能指标',
};

export default function MonitoringLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="zh-CN">
      <body>{children}</body>
    </html>
  );
}
