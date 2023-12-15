import { Pool } from "pg";

const pool = new Pool({
  connectionString: process.env.LANTERN_DB_PG_URI,
});

export const DBQuery = (text, params) => pool.query(text, params);
