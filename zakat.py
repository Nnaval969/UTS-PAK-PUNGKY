import mysql.connector
import pandas as pd
from tabulate import tabulate
from datetime import datetime
import sys

class DatabaseZakat:
    def __init__(self):
        self.db_config = {
            'host': 'localhost',
            'user': 'root',      # Ganti dengan username MySQL Anda
            'password': '',      # Ganti dengan password MySQL Anda
            'database': 'zakat_db'
        }
        self.connection = None
        self.connect()
        self.initialize_database()

    def connect(self):
        """Membuat koneksi ke database MySQL"""
        try:
            self.connection = mysql.connector.connect(**self.db_config)
            print("✅ Terhubung ke database MySQL berhasil!")
        except mysql.connector.Error as err:
            print(f"❌ Gagal terhubung ke MySQL: {err}")
            sys.exit(1)

    def initialize_database(self):
        """Menginisialisasi tabel jika belum ada"""
        try:
            cursor = self.connection.cursor()
            
            # Buat database jika belum ada
            cursor.execute("CREATE DATABASE IF NOT EXISTS zakat_db")
            cursor.execute("USE zakat_db")
            
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
                    kategori ENUM('Fakir', 'Miskin', 'Amil', 'Muallaf', 'Riqab', 
                                 'Gharim', 'Fisabilillah', 'Ibnu Sabil') NOT NULL,
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
            print("✅ Tabel berhasil diinisialisasi")
        except mysql.connector.Error as err:
            print(f"❌ Gagal inisialisasi database: {err}")
            sys.exit(1)

    def tambah_muzakki(self, data):
        """Menambahkan data muzakki baru"""
        query = """
            INSERT INTO muzakki (nama, alamat, no_hp, jenis_zakat, jumlah, tanggal)
            VALUES (%s, %s, %s, %s, %s, %s)
        """
        try:
            cursor = self.connection.cursor()
            cursor.execute(query, data)
            self.connection.commit()
            print("✅ Data muzakki berhasil ditambahkan")
            return cursor.lastrowid
        except mysql.connector.Error as err:
            print(f"❌ Gagal menambah muzakki: {err}")
            return None

    def lihat_muzakki(self, filter_tanggal=None):
        """Menampilkan data muzakki dengan opsi filter"""
        query = "SELECT * FROM muzakki"
        params = ()
        
        if filter_tanggal:
            query += " WHERE tanggal = %s"
            params = (filter_tanggal,)
            
        try:
            # Menggunakan pandas untuk membaca data dari MySQL
            df = pd.read_sql(query, self.connection, params=params)
            
            if not df.empty:
                # Format kolom jumlah
                df['jumlah'] = df.apply(
                    lambda row: f"{row['jumlah']} Kg" if row['jenis_zakat'] == 'Fitrah' 
                    else f"Rp {row['jumlah']:,.2f}", axis=1
                )
                
                print("\n📋 Daftar Muzakki:")
                print(tabulate(
                    df[['id', 'nama', 'jenis_zakat', 'jumlah', 'tanggal']], 
                    headers=['ID', 'Nama', 'Jenis Zakat', 'Jumlah', 'Tanggal'],
                    tablefmt='pretty',
                    showindex=False
                ))
                
                # Hitung total per jenis zakat
                totals = df['jenis_zakat'].value_counts()
                print("\n📊 Total per Jenis Zakat:")
                print(totals.to_string())
                
                return df
            else:
                print("❌ Tidak ada data muzakki yang ditemukan")
                return None
                
        except mysql.connector.Error as err:
            print(f"❌ Gagal membaca data: {err}")
            return None
        except pd.errors.DatabaseError as err:
            print(f"❌ Error pandas: {err}")
            return None

    def laporan_zakat(self):
        """Membuat laporan statistik zakat"""
        try:
            print("\n📈 Laporan Statistik Zakat")
            
            # Total zakat masuk per jenis
            query_masuk = """
                SELECT 
                    jenis_zakat AS 'Jenis Zakat',
                    COUNT(*) AS 'Jumlah Transaksi',
                    SUM(jumlah) AS 'Total Nilai'
                FROM muzakki
                GROUP BY jenis_zakat
            """
            df_masuk = pd.read_sql(query_masuk, self.connection)
            
            # Format nilai uang
            if not df_masuk.empty:
                df_masuk['Total Nilai'] = df_masuk.apply(
                    lambda row: f"{row['Total Nilai']} Kg" if row['Jenis Zakat'] == 'Fitrah' 
                    else f"Rp {row['Total Nilai']:,.2f}", axis=1
                )
                
                print("\n💵 Zakat Masuk:")
                print(tabulate(df_masuk, headers='keys', tablefmt='pretty', showindex=False))
            
            # Total distribusi zakat
            query_distribusi = """
                SELECT 
                    COUNT(*) AS 'Jumlah Distribusi',
                    SUM(jumlah) AS 'Total Distribusi'
                FROM distribusi_zakat
            """
            df_distribusi = pd.read_sql(query_distribusi, self.connection)
            
            if not df_distribusi.empty:
                print("\n📤 Distribusi Zakat:")
                print(tabulate(df_distribusi, headers='keys', tablefmt='pretty', showindex=False))
            
            return {
                'zakat_masuk': df_masuk,
                'distribusi': df_distribusi
            }
        except mysql.connector.Error as err:
            print(f"❌ Gagal membuat laporan: {err}")
            return None

    def close(self):
        """Menutup koneksi database"""
        if self.connection and self.connection.is_connected():
            self.connection.close()
            print("✅ Koneksi database ditutup")

def main_menu():
    print("\n" + "="*50)
    print("SISTEM MANAJEMEN ZAKAT".center(50))
    print("="*50)
    print("1. Tambah Data Muzakki")
    print("2. Lihat Data Muzakki")
    print("3. Laporan Statistik")
    print("4. Keluar")
    return input("Pilih menu (1-4): ")

def input_muzakki():
    print("\n" + "TAMBAH DATA MUZAKKI".center(50, "-"))
    nama = input("Nama Lengkap: ")
    alamat = input("Alamat: ")
    no_hp = input("No. HP: ")
    
    jenis_zakat = ""
    while jenis_zakat not in ['Fitrah', 'Maal']:
        jenis_zakat = input("Jenis Zakat (Fitrah/Maal): ").capitalize()
    
    satuan = "Kg" if jenis_zakat == "Fitrah" else "Rp"
    jumlah = float(input(f"Jumlah ({satuan}): "))
    
    tanggal = input("Tanggal (YYYY-MM-DD): ")
    try:
        datetime.strptime(tanggal, "%Y-%m-%d")
    except ValueError:
        print("❌ Format tanggal salah, menggunakan tanggal hari ini")
        tanggal = datetime.now().strftime("%Y-%m-%d")
    
    return (nama, alamat, no_hp, jenis_zakat, jumlah, tanggal)

def main():
    # Cek dependensi yang diperlukan
    try:
        import mysql.connector
        import pandas as pd
        from tabulate import tabulate
    except ImportError as e:
        print("\n❌ Modul yang diperlukan tidak terinstall!")
        print("Silakan install dengan perintah berikut:")
        print("pip install mysql-connector-python pandas tabulate")
        sys.exit(1)
    
    db = DatabaseZakat()
    
    while True:
        choice = main_menu()
        
        if choice == "1":
            data = input_muzakki()
            db.tambah_muzakki(data)
        
        elif choice == "2":
            filter_tanggal = input("Filter tanggal (YYYY-MM-DD, kosongkan untuk semua): ")
            db.lihat_muzakki(filter_tanggal if filter_tanggal else None)
        
        elif choice == "3":
            db.laporan_zakat()
        
        elif choice == "4":
            print("👋 Terima kasih, program selesai.")
            break
        
        else:
            print("❌ Pilihan tidak valid, silakan coba lagi")
        
        input("\nTekan Enter untuk melanjutkan...")
    
    db.close()

if __name__ == "__main__":
    main()