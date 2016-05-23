from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Column, Integer, String, Text


class Resultsdumpsqlite:

    def __init__():
        pass

Base = declarative_base()


class Companies(Base):
    __tablename__ = 'companies'

    id = Column(Integer, primary_key=True)
    company_name = Column(String(255))
    street_address = Column(String(255))
    postal_code = Column(Integer)
    locality = Column(String(255))
    firstdesc = Column(Text)
    secondesc = Column(Text)
    tel = Column(String(255))
    fax = Column(String(255))
    gsm = Column(String(255))
    siteweb = Column(String(255))
    email = Column(String(255))

    def __repr__(self):
        return "<Companies(name='%s', postal_code='%s', locality='%s')>" % (
            self.company_name, self.postal_code, self.locality)


def main():
    # engine = create_engine('sqlite:///:memory:', echo=True)
    print(repr(Companies.__table__))
    # ed_user = User(name='ed', fullname='Ed Jones', password='edspassword')
    # print(repr(ed_user))

if __name__ == '__main__':
    main()
