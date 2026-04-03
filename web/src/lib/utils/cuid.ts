/**
 * CUID 生成器
 *
 * 特性：
 * - 时间排序（36进制时间戳前缀）
 * - 全局唯一性（随机后缀 + 计数器）
 * - 简短可读（比UUID短）
 * - URL安全（仅使用 alphanumeric + _）
 *
 * 格式: c{时间戳36进制}_{随机后缀}_{计数器}
 * 示例: clx123abc_4f9z2_007
 */

// 模块级计数器，保证同一毫秒内的唯一性
let counter = 0;
let lastTimestamp = 0;

// 计数器重置阈值
const COUNTER_MAX = 1295; // 36^2 - 1

/**
 * 生成 CUID
 */
export function generateCUID(): string {
  const now = Date.now();

  // 重置计数器（如果进入新的毫秒）
  if (now !== lastTimestamp) {
    counter = 0;
    lastTimestamp = now;
  } else {
    counter++;
    // 如果计数器溢出，等待下一毫秒
    if (counter > COUNTER_MAX) {
      // 简单处理：阻塞等待下一毫秒
      while (Date.now() === now) {
        // busy wait
      }
      return generateCUID();
    }
  }

  // 时间戳转36进制
  const timePart = now.toString(36);

  // 随机部分（5字符）
  const randomPart = Math.random().toString(36).slice(2, 7);

  // 计数器部分（2字符，36进制填充）
  const counterPart = counter.toString(36).padStart(2, "0");

  return `c${timePart}_${randomPart}_${counterPart}`;
}

/**
 * 从 CUID 提取时间戳
 */
export function getTimestampFromCUID(cuid: string): number | null {
  const match = cuid.match(/^c([a-z0-9]+)_/);
  if (!match) return null;

  try {
    return parseInt(match[1], 36);
  } catch {
    return null;
  }
}

/**
 * 比较两个 CUID 的时间顺序
 * @returns 负数: a在b前, 0: 相同, 正数: a在b后
 */
export function compareCUID(a: string, b: string): number {
  const timeA = getTimestampFromCUID(a);
  const timeB = getTimestampFromCUID(b);

  if (timeA === null || timeB === null) {
    return a.localeCompare(b);
  }

  if (timeA !== timeB) {
    return timeA - timeB;
  }

  // 时间相同，按完整字符串比较（包含计数器）
  return a.localeCompare(b);
}

/**
 * 检查字符串是否是有效的 CUID
 */
export function isValidCUID(str: string): boolean {
  return /^c[a-z0-9]+_[a-z0-9]{5}_[a-z0-9]{2}$/.test(str);
}

/**
 * 生成短ID（简化版，用于非关键场景）
 */
export function generateShortId(): string {
  const time = Date.now().toString(36).slice(-4);
  const random = Math.random().toString(36).slice(2, 5);
  return `${time}${random}`;
}
