import { describe, expect, it } from 'vitest';
import { salaValida } from './sala';

describe('salaValida', () => {
  it('aceita 1 a 6', () => {
    for (const n of [1, 2, 3, 4, 5, 6]) expect(salaValida(String(n))).toBe(n);
  });
  it('recusa o resto', () => {
    for (const v of [null, '', '0', '7', '2.5', 'abc', '-1']) expect(salaValida(v)).toBeNull();
  });
});
