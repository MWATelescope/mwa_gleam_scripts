DEBUG = True
SECRET_KEY = "this is super secret"
SQLALCHEMY_DATABASE_URI = "postgresql://postgres:postgres@localhost/eor"
SQLALCHEMY_BINDS = {
    'mit': 'postgresql://mwa:BowTie@eor-db.mit.edu/mwa'
}
