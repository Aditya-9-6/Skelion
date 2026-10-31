import request from 'supertest';
import app from '../src/app';

describe('Health endpoint', () => {
  it('should respond 200 with JSON status ok', async () => {
    const res = await request(app).get('/healthz').expect(200);
    expect(res.body).toEqual({ status: 'ok' });
  });
});
