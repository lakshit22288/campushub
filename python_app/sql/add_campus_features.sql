CREATE TABLE IF NOT EXISTS campus_events (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  title TEXT NOT NULL,
  description TEXT NOT NULL,
  location TEXT NOT NULL DEFAULT '',
  starts_at TIMESTAMPTZ NOT NULL,
  ends_at TIMESTAMPTZ NOT NULL,
  target_branch_id UUID REFERENCES branches(id) ON DELETE SET NULL,
  created_by UUID REFERENCES users(id) ON DELETE SET NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  CONSTRAINT campus_events_valid_time CHECK (ends_at > starts_at)
);

CREATE INDEX IF NOT EXISTS campus_events_starts_at_idx
  ON campus_events (starts_at);
CREATE INDEX IF NOT EXISTS campus_events_target_branch_idx
  ON campus_events (target_branch_id);

CREATE TABLE IF NOT EXISTS schedule_entries (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  course TEXT NOT NULL,
  day_of_week SMALLINT NOT NULL CHECK (day_of_week BETWEEN 0 AND 6),
  start_time TIME NOT NULL,
  end_time TIME NOT NULL,
  location TEXT NOT NULL DEFAULT '',
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  CONSTRAINT schedule_entries_valid_time CHECK (end_time > start_time)
);

CREATE INDEX IF NOT EXISTS schedule_entries_user_day_time_idx
  ON schedule_entries (user_id, day_of_week, start_time);

CREATE TABLE IF NOT EXISTS assignment_entries (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  title TEXT NOT NULL,
  subject TEXT NOT NULL DEFAULT '',
  due_date DATE NOT NULL,
  notes TEXT NOT NULL DEFAULT '',
  completed BOOLEAN NOT NULL DEFAULT FALSE,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS assignment_entries_user_due_date_idx
  ON assignment_entries (user_id, completed, due_date);
