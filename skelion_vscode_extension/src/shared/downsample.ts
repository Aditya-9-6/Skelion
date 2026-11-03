/**
 * Largest-Triangle-Three-Buckets (LTTB) downsampling algorithm.
 * Downsamples time-series data points to a target threshold while preserving visual peaks and troughs.
 */

export interface DataPoint {
  x: number; // numeric timestamp or index
  y: number; // numeric metric value
  original?: unknown;
}

export function downsampleLTTB<T extends { [key: string]: any }>(
  data: T[],
  threshold: number,
  xAccessor: (item: T) => number,
  yAccessor: (item: T) => number
): T[] {
  if (threshold >= data.length || threshold === 0) {
    return data; // No downsampling needed
  }

  const sampled: T[] = [];
  const bucketSize = (data.length - 2) / (threshold - 2);

  let a = 0; // First point of the previous bucket
  sampled.push(data[a]);

  for (let i = 0; i < threshold - 2; i++) {
    // Calculate point average for next bucket (bucket c)
    let avgX = 0;
    let avgY = 0;
    const avgRangeStart = Math.floor((i + 1) * bucketSize) + 1;
    const avgRangeEnd = Math.min(Math.floor((i + 2) * bucketSize) + 1, data.length);
    const avgRangeLength = avgRangeEnd - avgRangeStart;

    for (let j = avgRangeStart; j < avgRangeEnd; j++) {
      avgX += xAccessor(data[j]);
      avgY += yAccessor(data[j]);
    }
    avgX /= (avgRangeLength || 1);
    avgY /= (avgRangeLength || 1);

    // Get the range for this bucket (bucket b)
    const rangeBStart = Math.floor(i * bucketSize) + 1;
    const rangeBEnd = Math.min(Math.floor((i + 1) * bucketSize) + 1, data.length);

    // Point a
    const pointAX = xAccessor(data[a]);
    const pointAY = yAccessor(data[a]);

    let maxArea = -1;
    let maxAreaIndex = rangeBStart;

    for (let j = rangeBStart; j < rangeBEnd; j++) {
      // Triangle area: 0.5 * |x_a(y_b - y_c) + x_b(y_c - y_a) + x_c(y_a - y_b)|
      const area = Math.abs(
        (pointAX - avgX) * (yAccessor(data[j]) - pointAY) -
        (pointAX - xAccessor(data[j])) * (avgY - pointAY)
      ) * 0.5;

      if (area > maxArea) {
        maxArea = area;
        maxAreaIndex = j;
      }
    }

    sampled.push(data[maxAreaIndex]);
    a = maxAreaIndex; // Next a is this bucket's selected point
  }

  // Always include the last point
  sampled.push(data[data.length - 1]);
  return sampled;
}
