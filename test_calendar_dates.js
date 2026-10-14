const assert = require('node:assert/strict');
const dates = require('./calendar.js');

// Published Easter dates, including leap years and the non-leap century 2100.
for (const [year, easter] of [[2026,'2026-04-05'],[2027,'2027-03-28'],[2028,'2028-04-16'],[2029,'2029-04-01'],[2030,'2030-04-21'],[2038,'2038-04-25'],[2100,'2100-03-28']]) {
    const holidays = dates.holidays(year);
    assert.equal(holidays.size, 13);
    for (const [offset,name] of [[1,'Ostermontag'],[39,'Christi Himmelfahrt'],[50,'Pfingstmontag'],[60,'Fronleichnam']]) {
        assert.equal(holidays.get(dates.shift(easter, offset)), name);
    }
    assert.equal(holidays.get(`${year}-10-26`), 'Nationalfeiertag');
}
assert.equal(dates.shift('2028-02-28',1), '2028-02-29');
assert.equal(dates.shift('2100-02-28',1), '2100-03-01');
assert.equal(dates.parse('2027-01-01').getUTCDay(), 5);
assert.equal(dates.parse('2028-01-01').getUTCDay(), 6);
assert.equal(dates.weekStart('2027-01-01'), '2026-12-28');
assert.equal(dates.shift('2026-03-29',1), '2026-03-30');
assert.equal(dates.key(new Date('2026-10-13T22:30:00Z')), '2026-10-14');
const event = {id:'a',startAt:'2026-10-14T11:00:00+02:00'};
assert.equal(dates.uniqueEvents([
    {...event, externalId:'42'}, {...event,id:'copy',externalId:'42'},
    {...event,id:'different',externalId:'43'}]).length,2);
const start = new Date(event.startAt).getTime();
assert(!dates.reminderDue(event,start-1800001));
assert(dates.reminderDue(event,start-1800000));
assert(!dates.reminderDue(event,start));
assert(!dates.reminderDue({...event,allDay:true},start-1800000));
assert.notEqual(dates.reminderKey(event), dates.reminderKey({...event,startAt:'2026-10-15T11:00:00+02:00'}));
console.log('Future holidays, weekdays, leap years, Vienna time and reminder boundaries: passed');
