from sqlalchemy import create_engine, Column, Integer, String, ForeignKey, Date, Numeric, Enum, LargeBinary
from sqlalchemy.orm import declarative_base, relationship, sessionmaker
import enum

Base = declarative_base()

# Определение ENUM типов
class Pol(enum.Enum):
    M = "Мужской"
    J = "Женский"

class NazvanieDolzhnosti(enum.Enum):
    Direktor = "Директор"
    Operator_florist = "Оператор-флорист"

class TipTovara(enum.Enum):
    Buket = "Букет"
    Cvetok = "Цветок"
    Kompoziciay = "Композиция"
    Na_svadbu = "На свадьбу"
    Komnatn_rost = "Комнатные растения" 
    Florarium = "Флорариумы"
    Podarki = "Подарки"
    Popular = "Популярное"

class TipPostavshika(enum.Enum):
    OOO = "ООО"
    AO = "АО"
    OAO = "ОАО"
    IP = "ИП"
    ZAO = "ЗАО"

# Таблицы базы данных
class Oblast(Base):
    __tablename__ = "oblast"
    id = Column(Integer, primary_key=True)
    nazvanie = Column(String(100), nullable=False)
    goroda = relationship("Gorod", back_populates="oblast")

class Gorod(Base):
    __tablename__ = "gorod"
    id = Column(Integer, primary_key=True)
    nazvanie = Column(String(100), nullable=False)
    sok_nazvanie = Column(String(100), nullable=False)
    oblast_id = Column(Integer, ForeignKey("oblast.id"))
    oblast = relationship("Oblast", back_populates="goroda")
    ulicy = relationship("Ulica", back_populates="gorod")

class Ulica(Base):
    __tablename__ = "ulica"
    id = Column(Integer, primary_key=True)
    nazvanie = Column(String(100), nullable=False)
    gorod_id = Column(Integer, ForeignKey("gorod.id"))
    gorod = relationship("Gorod", back_populates="ulicy")
    doma = relationship("DomStroenie", back_populates="ulica")

class DomStroenie(Base):
    __tablename__ = "dom_stroenie"
    id = Column(Integer, primary_key=True)
    nomer = Column(Integer, nullable=False)
    ulica_id = Column(Integer, ForeignKey("ulica.id"))
    ulica = relationship("Ulica", back_populates="doma")
    postavshiki = relationship("Postavshik", back_populates="juridicheskij_adres_rel")

class Postavshik(Base):
    __tablename__ = "postavshik"
    id = Column(Integer, primary_key=True)
    nazvanie_postavshika = Column(String(100), nullable=False)
    tip_postavshika = Column(Enum(TipPostavshika), nullable=False)
    kontakt_tel = Column(String(100))
    email = Column(String(100))
    juridicheskij_adres = Column(Integer, ForeignKey("dom_stroenie.id"))
    juridicheskij_adres_rel = relationship("DomStroenie", back_populates="postavshiki") 
    podrobnosti = relationship("PodrobnaiaInformacijaOPostavshike", back_populates="postavshik")
    tovar = relationship("Tovar", back_populates="postavshik")
    otchety_postuplenija = relationship("OtchetyPoPostuplenijuTovarov", back_populates="postavshik")

class Dokument(Base):
    __tablename__ = "dokument"
    id = Column(Integer, primary_key=True)
    seria = Column(Integer, nullable=False)
    nomer = Column(Integer, nullable=False)
    data_vidachi = Column(Date)
    kem_vidan = Column(String(100))
    postavshik_info = relationship("PodrobnaiaInformacijaOPostavshike", back_populates="dokument")
    sotrudnik_info = relationship("PodrobnaiaInformacijaOSotrudnike", back_populates="dokument")

class PodrobnaiaInformacijaOPostavshike(Base):
    __tablename__ = "podrobnaia_informacija_o_postavshike"
    id = Column(Integer, primary_key=True)
    postavshik_id = Column(Integer, ForeignKey("postavshik.id"))
    dokument_id = Column(Integer, ForeignKey("dokument.id"))
    postavshik = relationship("Postavshik", back_populates="podrobnosti")
    dokument = relationship("Dokument", back_populates="postavshik_info")

class Tovar(Base):
    __tablename__ = "tovar"
    id = Column(Integer, primary_key=True)
    nazvanie = Column(Enum(TipTovara), nullable=False)
    nomer = Column(Integer, nullable=False)
    opisanie = Column(String(100))
    cena = Column(Numeric(10, 2))
    kartinka = Column(LargeBinary)
    postavshik_id = Column(Integer, ForeignKey("postavshik.id"))
    postavshik = relationship("Postavshik", back_populates="tovar")
    otchety_postuplenija = relationship("OtchetyPoPostuplenijuTovarov", back_populates="tovar")
    otchety_ostatki = relationship("OtchetyPoOstatkamTovarov", back_populates="tovar")
    otchety_ubytie = relationship("OtchetyPoUbytomuTovaru", back_populates="tovar")

class Sotrudnik(Base):
    __tablename__ = "sotrudnik"
    id = Column(Integer, primary_key=True)
    familiya = Column(String(100), nullable=False)
    imya = Column(String(100), nullable=False)
    otchestvo = Column(String(100))
    data_rozhdeniya = Column(Date) 
    inn = Column(Integer)
    snils = Column(Integer)
    pol = Column(Enum(Pol), nullable=False)
    podrobnosti = relationship("PodrobnaiaInformacijaOSotrudnike", back_populates="sotrudnik")

class PodrobnaiaInformacijaOSotrudnike(Base):
    __tablename__ = "podrobnaia_informacija_o_sotrudnike"
    id = Column(Integer, primary_key=True)
    sotrudnik_id = Column(Integer, ForeignKey("sotrudnik.id"))
    dokument_id = Column(Integer, ForeignKey("dokument.id"))
    sotrudnik = relationship("Sotrudnik", back_populates="podrobnosti")
    dokument = relationship("Dokument", back_populates="sotrudnik_info")

class FormirovanieOtcheta(Base):
    __tablename__ = "formirovanie_otcheta"
    id = Column(Integer, primary_key=True)
    nazvanie = Column(String(100), nullable=False)
    kratkoe_opisanie = Column(String(100))
    polnoe_opisanie = Column(String(250))
    dolzhnosti = relationship("Dolzhnost", back_populates="formirovanie_otcheta")

class Dolzhnost(Base):
    __tablename__ = "dolzhnost"
    id = Column(Integer, primary_key=True)
    nazvanie = Column(Enum(NazvanieDolzhnosti), nullable=False)
    kratkoe_opisanie = Column(String(100))
    polnoe_opisanie = Column(String(250))
    data_priema = Column(Date)
    data_ugovorzenia = Column(Date)
    formirovanie_otcheta_id = Column(Integer, ForeignKey("formirovanie_otcheta.id"))
    formirovanie_otcheta = relationship("FormirovanieOtcheta", back_populates="dolzhnosti")

class OtchetyPoPostuplenijuTovarov(Base):
    __tablename__ = "otchety_po_postupleniju_tovarov"
    id = Column(Integer, primary_key=True)
    data_postuplenija = Column(Date, nullable=False)
    kolithestvo_postupivshih_tovarov = Column(Integer, nullable=False)
    data_formirovaniya_otcheta = Column(Date, nullable=False)
    tovar_id = Column(Integer, ForeignKey("tovar.id"))
    postavshik_id = Column(Integer, ForeignKey("postavshik.id"))
    tovar = relationship("Tovar", back_populates="otchety_postuplenija")
    postavshik = relationship("Postavshik", back_populates="otchety_postuplenija")

class OtchetyPoOstatkamTovarov(Base):
    __tablename__ = "otchety_po_ostatkom_tovarov"
    id = Column(Integer, primary_key=True)
    kolithestvo_tovara = Column(Integer, nullable=False)
    data_formirovaniya_otcheta = Column(Date, nullable=False)
    tovar_id = Column(Integer, ForeignKey("tovar.id"))
    tovar = relationship("Tovar", back_populates="otchety_ostatki")

class OtchetyPoUbytomuTovaru(Base):
    __tablename__ = "otchety_po_ubytomu_tovaru"
    id = Column(Integer, primary_key=True)
    data_ubytija = Column(Date, nullable=False)
    kolithestvo_ubytogo_tovara = Column(Integer, nullable=False)
    data_formirovaniya_otcheta = Column(Date, nullable=False)
    tovar_id = Column(Integer, ForeignKey("tovar.id"))
    tovar = relationship("Tovar", back_populates="otchety_ubytie")

class Connect:
    @staticmethod
    def create_session():
        engine = create_engine("postgresql://postgres:1@localhost:5433/postgres") 
        Base.metadata.create_all(engine)
        Session = sessionmaker(bind=engine)
        session = Session()
        return session