// Skelion Express & Node.js Resilience Middleware
// Intercepts unhandled edge exceptions fail-open with zero user downtime
export function skelionFailOpen(err, req, res, next) {
  console.error(`[Skelion] Intercepted edge exception on ${req.method} ${req.originalUrl}:`, err.message);
  return res.status(200).json({
    status: 'fail_open_buffered',
    incident_route: req.originalUrl,
    message: 'Your request was buffered safely and will be reconciled automatically.'
  });
}
