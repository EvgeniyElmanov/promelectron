import { describe, it, expect } from 'vitest';
import {
  formatShortDate,
  formatDate,
  formatTime,
  formatDateTime,
  formatDateTimeShort,
} from '@/utils/date';

const NOON_UTC = '2026-05-18T12:00:00Z';
const TIME_UTC = '2026-05-18T10:05:09Z';

describe('date utils', () => {
  describe('formatShortDate', () => {
    it('returns DD.MM with leading zeros', () => {
      expect(formatShortDate(NOON_UTC)).toBe('18.05');
    });

    it('returns — for empty input', () => {
      expect(formatShortDate('')).toBe('—');
      expect(formatShortDate(null)).toBe('—');
      expect(formatShortDate(undefined)).toBe('—');
    });

    it('returns — for invalid date string', () => {
      expect(formatShortDate('not-a-date')).toBe('—');
    });
  });

  describe('formatDate', () => {
    it('returns DD.MM.YYYY with leading zeros', () => {
      expect(formatDate(NOON_UTC)).toBe('18.05.2026');
    });

    it('keeps the same day for noon UTC in most timezones', () => {
      expect(formatDate(NOON_UTC)).toMatch(/^\d{2}\.\d{2}\.\d{4}$/);
      const [, day] = formatDate(NOON_UTC).split('.');
      expect(day).toBe('05');
    });

    it('returns — for empty input', () => {
      expect(formatDate('')).toBe('—');
      expect(formatDate(null)).toBe('—');
      expect(formatDate(undefined)).toBe('—');
    });

    it('returns — for invalid date string', () => {
      expect(formatDate('invalid')).toBe('—');
    });
  });

  describe('formatTime', () => {
    it('returns HH:MM:SS in 24-hour format with leading zeros', () => {
      expect(formatTime(TIME_UTC)).toMatch(/^\d{2}:\d{2}:\d{2}$/);
    });

    it('returns — for empty input', () => {
      expect(formatTime('')).toBe('—');
      expect(formatTime(null)).toBe('—');
      expect(formatTime(undefined)).toBe('—');
    });

    it('returns — for invalid date string', () => {
      expect(formatTime('bad-time')).toBe('—');
    });
  });

  describe('formatDateTime', () => {
    it('combines formatDate and formatTime separated by ", "', () => {
      const result = formatDateTime(TIME_UTC);
      const [datePart, timePart] = result.split(', ');
      expect(datePart).toBe(formatDate(TIME_UTC));
      expect(timePart).toBe(formatTime(TIME_UTC));
      expect(result).toMatch(/^\d{2}\.\d{2}\.\d{4}, \d{2}:\d{2}:\d{2}$/);
    });

    it('returns — for empty input', () => {
      expect(formatDateTime('')).toBe('—');
      expect(formatDateTime(null)).toBe('—');
      expect(formatDateTime(undefined)).toBe('—');
    });

    it('returns — for invalid date string', () => {
      expect(formatDateTime('not-a-date')).toBe('—');
    });
  });

  describe('formatDateTimeShort', () => {
    it('returns DD.MM.YYYY HH:MM separated by a space, without seconds', () => {
      const result = formatDateTimeShort(TIME_UTC);
      const [datePart, timePart] = result.split(' ');
      expect(datePart).toBe(formatDate(TIME_UTC));
      expect(timePart).toMatch(/^\d{2}:\d{2}$/);
      expect(result).toMatch(/^\d{2}\.\d{2}\.\d{4} \d{2}:\d{2}$/);
    });

    it('does not include seconds', () => {
      const result = formatDateTimeShort(TIME_UTC);
      expect(result.split(':').length).toBe(2);
    });

    it('returns — for empty input', () => {
      expect(formatDateTimeShort('')).toBe('—');
      expect(formatDateTimeShort(null)).toBe('—');
      expect(formatDateTimeShort(undefined)).toBe('—');
    });

    it('returns — for invalid date string', () => {
      expect(formatDateTimeShort('not-a-date')).toBe('—');
    });
  });
});
