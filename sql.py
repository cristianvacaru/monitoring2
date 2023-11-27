
import sqlite3

conn = sqlite3.connect('np_database.db')
c = conn.cursor()
# c.execute(f'DROP TABLE codAviz_data')
c.execute('ALTER TABLE np_data ADD COLUMN volum REAL;')
c.execute('ALTER TABLE np_data ADD COLUMN volumRasinoase REAL;')
c.execute('ALTER TABLE np_data ADD COLUMN exploatari TEXT;')
c.execute('ALTER TABLE np_data ADD COLUMN prelungiri TEXT;')
c.execute('ALTER TABLE np_data ADD COLUMN codStare INTEGER;')
# c.execute(f'UPDATE codAviz_data SET sent_status = 0')
conn.commit()
conn.close()