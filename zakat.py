try:
    import pandas as pd
    import pymysql
    from tabulate import tabulate
except ImportError as e:
    print("\nERROR: Modul yang diperlukan tidak ditemukan!")
    print(f"Detail error: {e}")
    print("\nSilakan install modul yang diperlukan dengan perintah berikut:")
    print("\nJika menggunakan Python 3.x, coba: python3 -m pip install nama_modul")
    exit(1)
from datetime import datetime

class DatabaseZakat:
    def __init__(self):
        self.db_config = {
            'host': 'localhost',
            'user': 'root',  # Ganti dengan username MySQL Anda
            'password': '',  # Ganti dengan password MySQL Anda
            'database': 'zakat_db'
        }
        self.connection = None
        self.connect()
        self.initialize_database()

    def connect(self):
        """Membuat koneksi ke database MySQL"""
        try:
            self.connection = pymysql.connect(**self.db_config)
            print("Terhubung ke database MySQL berhasil!")
        except pymysql.Error as e:
            print(f"Error connecting to MySQL: {e}")
            raise

    def initialize_database(self):
        """Menginisialisasi tabel jika belum ada"""
        try:
            with self.connection.cursor() as cursor:
                # Tabel muzakki (pembayar zakat)
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS muzakki (
                        id INT AUTO_INCREMENT PRIMARY KEY,
                        nama VARCHAR(100) NOT NULL,
                        alamat TEXT,
                        no_hp VARCHAR(20),
                        jenis_zakat ENUM('Fitrah', 'Maal') NOT NULL,
                        jumlah DECIMAL(10,2) NOT NULL,
                        tanggal DATE NOT NULL,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                
                # Tabel mustahik (penerima zakat)
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS mustahik (
                        id INT AUTO_INCREMENT PRIMARY KEY,
                        nama VARCHAR(100) NOT NULL,
                        alamat TEXT,
                        no_hp VARCHAR(20),
                        kategori ENUM('Fakir', 'Miskin', 'Amil', 'Muallaf', 'Riqab', 'Gharim', 'Fisabilillah', 'Ibnu Sabil') NOT NULL,
                        jumlah DECIMAL(10,2) NOT NULL,
                        tanggal DATE NOT NULL,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                
                # Tabel distribusi zakat
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS distribusi_zakat (
                        id INT AUTO_INCREMENT PRIMARY KEY,
                        mustahik_id INT,
                        jumlah DECIMAL(10,2) NOT NULL,
                        tanggal DATE NOT NULL,
                        keterangan TEXT,
                        FOREIGN KEY (mustahik_id) REFERENCES mustahik(id)
                    )
                """)
                
            self.connection.commit()
            print("Tabel berhasil diinisialisasi")
        except pymysql.Error as e:
            print(f"Error initializing database: {e}")
            raise

    def tambah_muzakki(self, data):
        """Menambahkan data muzakki baru"""
        query = """
            INSERT INTO muzakki (nama, alamat, no_hp, jenis_zakat, jumlah, tanggal)
            VALUES (%s, %s, %s, %s, %s, %s)
        """
        try:
            with self.connection.cursor() as cursor:
                cursor.execute(query, data)
            self.connection.commit()
            print("Data muzakki berhasil ditambahkan")
            return cursor.lastrowid
        except pymysql.Error as e:
            print(f"Error adding muzakki: {e}")
            return None

    def lihat_muzakki(self, filter_tanggal=None):
        """Menampilkan data muzakki dengan opsi filter"""
        query = "SELECT * FROM muzakki"
        params = ()
        
        if filter_tanggal:
            query += " WHERE tanggal = %s"
            params = (filter_tanggal,)
            
        try:
            df = pd.read_sql(query, self.connection, params=params)
            
            if not df.empty:
                # Format kolom jumlah
                df['jumlah'] = df.apply(
                    lambda row: f"{row['jumlah']} Kg" if row['jenis_zakat'] == 'Fitrah' 
                    else f"Rp {row['jumlah']:,.2f}", axis=1
                )
                
                print("\nDaftar Muzakki:")
                print(tabulate(df[['id', 'nama', 'jenis_zakat', 'jumlah', 'tanggal']], 
                              headers='keys', tablefmt='psql', showindex=False))
                
                # Hitung total per jenis zakat
                totals = df.groupby('jenis_zakat')['jumlah'].count()
                print("\nTotal per Jenis Zakat:")
                print(totals.to_string())
                
                return df
            else:
                print("Tidak ada data muzakki yang ditemukan")
                return None
                
        except pymysql.Error as e:
            print(f"Error viewing muzakki: {e}")
            return None

    def laporan_zakat(self):
        """Membuat laporan statistik zakat"""
        try:
            # Total zakat masuk per jenis
            query_masuk = """
                SELECT jenis_zakat, SUM(jumlah) as total, COUNT(*) as jumlah_transaksi
                FROM muzakki
                GROUP BY jenis_zakat
            """
            df_masuk = pd.read_sql(query_masuk, self.connection)
            
            # Total distribusi zakat
            query_distribusi = """
                SELECT SUM(d.jumlah) as total_distribusi, COUNT(*) as jumlah_distribusi
                FROM distribusi_zakat d
            """
            df_distribusi = pd.read_sql(query_distribusi, self.connection)
            
            print("\nLaporan Zakat:")
            print("\nZakat Masuk:")
            print(tabulate(df_masuk, headers='keys', tablefmt='psql', showindex=False))
            
            print("\nDistribusi Zakat:")
            print(tabulate(df_distribusi, headers='keys', tablefmt='psql', showindex=False))
            
            return {
                'zakat_masuk': df_masuk,
                'distribusi': df_distribusi
            }
        except pymysql.Error as e:
            print(f"Error generating report: {e}")
            return None

    def close(self):
        """Menutup koneksi database"""
        if self.connection:
            self.connection.close()
            print("Koneksi database ditutup")

def main():
    db = DatabaseZakat()
    
    while True:
        print("\n=== Sistem Manajemen Zakat ===")
        print("1. Tambah Muzakki")
        print("2. Lihat Data Muzakki")
        print("3. Laporan Zakat")
        print("4. Keluar")
        
        choice = input("Pilih menu (1-4): ")
        
        if choice == "1":
            print("\nTambah Data Muzakki")
            nama = input("Nama: ")
            alamat = input("Alamat: ")
            no_hp = input("No HP: ")
            
            jenis_zakat = ""
            while jenis_zakat not in ['Fitrah', 'Maal']:
                jenis_zakat = input("Jenis Zakat (Fitrah/Maal): ").capitalize()
            
            jumlah = float(input(f"Jumlah ({'Kg' if jenis_zakat == 'Fitrah' else 'Rp'}): "))
            tanggal = input("Tanggal (YYYY-MM-DD): ")
            
            data = (nama, alamat, no_hp, jenis_zakat, jumlah, tanggal)
            db.tambah_muzakki(data)
            
        elif choice == "2":
            filter_tanggal = input("Filter berdasarkan tanggal (YYYY-MM-DD, kosongkan untuk semua): ")
            db.lihat_muzakki(filter_tanggal if filter_tanggal else None)
            
        elif choice == "3":
            db.laporan_zakat()
            
        elif choice == "4":
            print("Keluar dari program...")
            break
            
        else:
            print("Pilihan tidak valid, silakan coba lagi")
    
    db.close()

if __name__ == "__main__":
    main()