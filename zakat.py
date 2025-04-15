import mysql.connector
import pandas as pd
from tabulate import tabulate
from datetime import datetime
import sys

class DatabaseManager:
    def __init__(self):
        self.connection = None
        self.config = {
            'host': 'localhost',
            'user': 'root',
            'password': '',  # Set your MySQL password here
            'database': 'zakat_db'
        }

    def connect(self):
        """Membuat koneksi ke database MySQL"""
        try:
            # Pertama coba terhubung tanpa database tertentu
            temp_config = self.config.copy()
            temp_config.pop('database')  # Hapus database dari config sementara
            
            temp_conn = mysql.connector.connect(**temp_config)
            cursor = temp_conn.cursor()
            
            # Buat database jika belum ada
            cursor.execute(f"CREATE DATABASE IF NOT EXISTS {self.config['database']}")
            cursor.close()
            temp_conn.close()
            
            # Sekarang terhubung dengan database yang sudah dipastikan ada
            self.connection = mysql.connector.connect(**self.config)
            print("✅ Berhasil terhubung ke database MySQL")
            return True
            
        except mysql.connector.Error as err:
            print(f"❌ Gagal terhubung ke MySQL: {err}")
            return False

    def initialize_database(self):
        """Menginisialisasi database dan tabel"""
        try:
            cursor = self.connection.cursor()
            
            # Gunakan database yang sudah dibuat
            cursor.execute(f"USE {self.config['database']}")
            
            # Daftar query untuk membuat tabel
            tables = {
                'muzakki': """
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
                """,
                'mustahik': """
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
                """,
                'distribusi_zakat': """
                    CREATE TABLE IF NOT EXISTS distribusi_zakat (
                        id INT AUTO_INCREMENT PRIMARY KEY,
                        mustahik_id INT,
                        jumlah DECIMAL(10,2) NOT NULL,
                        tanggal DATE NOT NULL,
                        keterangan TEXT,
                        FOREIGN KEY (mustahik_id) REFERENCES mustahik(id)
                    )
                """
            }
            
            # Eksekusi pembuatan tabel
            for table_name, query in tables.items():
                cursor.execute(query)
                print(f"✅ Tabel {table_name} berhasil dibuat/diverifikasi")
            
            self.connection.commit()
            return True
            
        except mysql.connector.Error as err:
            print(f"❌ Gagal inisialisasi database: {err}")
            return False
        finally:
            if self.connection.is_connected():
                cursor.close()

    # ... (metode lainnya tetap sama)

    def execute_query(self, query, params=None, fetch=False):
        """Eksekusi query dengan penanganan error"""
        try:
            cursor = self.connection.cursor(dictionary=True)
            cursor.execute(query, params or ())
            
            if fetch:
                result = cursor.fetchall()
                return pd.DataFrame(result) if result else None
            
            self.connection.commit()
            return True
            
        except mysql.connector.Error as err:
            print(f"❌ Error SQL: {err}")
            return None
        finally:
            if self.connection.is_connected():
                cursor.close()

    def close(self):
        """Menutup koneksi database"""
        if self.connection and self.connection.is_connected():
            self.connection.close()
            print("✅ Koneksi database ditutup")

class ZakatApp:
    def __init__(self):
        self.db = DatabaseManager()
        self.start_app()

    def start_app(self):
        """Memulai aplikasi"""
        if not self.db.connect():
            sys.exit(1)
            
        if not self.db.initialize_database():
            sys.exit(1)
            
        self.main_menu()

    def display_table(self, df, title):
        """Menampilkan dataframe dalam format tabel"""
        if df is None or df.empty:
            print(f"❌ Tidak ada data {title} yang ditemukan")
            return
        
        print(f"\n📋 {title}:")
        print(tabulate(
            df, 
            headers='keys', 
            tablefmt='pretty',
            showindex=False,
            numalign="center",
            stralign="left"
        ))

    def tambah_muzakki(self):
        """Menambahkan data muzakki baru"""
        print("\n" + " TAMBAH DATA MUZAKKI ".center(50, "="))
        
        data = {
            'nama': input("Nama Lengkap: ").strip(),
            'alamat': input("Alamat: ").strip(),
            'no_hp': input("No. HP: ").strip(),
            'jenis_zakat': self.pilih_jenis_zakat(),
            'jumlah': self.input_jumlah_zakat(),
            'tanggal': self.input_tanggal()
        }
        
        query = """
            INSERT INTO muzakki (nama, alamat, no_hp, jenis_zakat, jumlah, tanggal)
            VALUES (%(nama)s, %(alamat)s, %(no_hp)s, %(jenis_zakat)s, %(jumlah)s, %(tanggal)s)
        """
        
        if self.db.execute_query(query, data):
            print("✅ Data muzakki berhasil ditambahkan")

    def pilih_jenis_zakat(self):
        """Memilih jenis zakat dengan validasi"""
        while True:
            jenis = input("Jenis Zakat (Fitrah/Maal): ").capitalize()
            if jenis in ['Fitrah', 'Maal']:
                return jenis
            print("❌ Pilihan tidak valid. Silakan pilih Fitrah atau Maal")

    def input_jumlah_zakat(self):
        """Input jumlah zakat dengan validasi"""
        while True:
            try:
                jumlah = float(input("Jumlah (Kg untuk Fitrah, Rp untuk Maal): "))
                if jumlah > 0:
                    return jumlah
                print("❌ Jumlah harus lebih dari 0")
            except ValueError:
                print("❌ Harap masukkan angka yang valid")

    def input_tanggal(self):
        """Input tanggal dengan validasi"""
        while True:
            tanggal = input("Tanggal (YYYY-MM-DD): ").strip()
            try:
                datetime.strptime(tanggal, "%Y-%m-%d")
                return tanggal
            except ValueError:
                print("❌ Format tanggal salah. Gunakan format YYYY-MM-DD")

    def lihat_muzakki(self):
        """Menampilkan data muzakki dengan filter"""
        print("\n" + " DATA MUZAKKI ".center(50, "="))
        
        filter_tanggal = input("Filter berdasarkan tanggal (YYYY-MM-DD, kosongkan untuk semua): ").strip()
        
        query = "SELECT * FROM muzakki"
        params = None
        
        if filter_tanggal:
            try:
                datetime.strptime(filter_tanggal, "%Y-%m-%d")
                query += " WHERE tanggal = %s"
                params = (filter_tanggal,)
            except ValueError:
                print("❌ Format tanggal filter tidak valid, menampilkan semua data")
        
        df = self.db.execute_query(query, params, fetch=True)
        
        if df is not None:
            # Format tampilan jumlah
            df['jumlah'] = df.apply(
                lambda row: f"{row['jumlah']} Kg" if row['jenis_zakat'] == 'Fitrah' 
                else f"Rp {row['jumlah']:,.2f}", 
                axis=1
            )
            
            # Hanya tampilkan kolom tertentu
            display_cols = ['id', 'nama', 'jenis_zakat', 'jumlah', 'tanggal']
            self.display_table(df[display_cols], "Daftar Muzakki")
            
            # Hitung statistik
            self.tampilkan_statistik_muzakki(df)

    def tampilkan_statistik_muzakki(self, df):
        """Menampilkan statistik data muzakki"""
        if df.empty:
            return
            
        total_fitrah = df[df['jenis_zakat'] == 'Fitrah']['jumlah'].count()
        total_maal = df[df['jenis_zakat'] == 'Maal']['jumlah'].count()
        
        print("\n📊 Statistik:")
        print(f"Total Zakat Fitrah: {total_fitrah} transaksi")
        print(f"Total Zakat Maal: {total_maal} transaksi")
        
        if not df.empty:
            print(f"\n📅 Periode: {df['tanggal'].min()} hingga {df['tanggal'].max()}")

    def laporan_zakat(self):
        """Membuat laporan statistik zakat"""
        print("\n" + " LAPORAN ZAKAT ".center(50, "="))
        
        # Laporan zakat masuk
        query_masuk = """
            SELECT 
                jenis_zakat AS 'Jenis Zakat',
                COUNT(*) AS 'Jumlah Transaksi',
                SUM(jumlah) AS 'Total Nilai'
            FROM muzakki
            GROUP BY jenis_zakat
        """
        
        df_masuk = self.db.execute_query(query_masuk, fetch=True)
        if df_masuk is not None and not df_masuk.empty:
            # Format nilai
            df_masuk['Total Nilai'] = df_masuk.apply(
                lambda row: f"{row['Total Nilai']} Kg" if row['Jenis Zakat'] == 'Fitrah' 
                else f"Rp {row['Total Nilai']:,.2f}", 
                axis=1
            )
            self.display_table(df_masuk, "Zakat Masuk")
        
        # Laporan distribusi
        query_distribusi = """
            SELECT 
                m.kategori AS 'Kategori Mustahik',
                COUNT(d.id) AS 'Jumlah Distribusi',
                SUM(d.jumlah) AS 'Total Distribusi'
            FROM distribusi_zakat d
            RIGHT JOIN mustahik m ON d.mustahik_id = m.id
            GROUP BY m.kategori
        """
        
        df_distribusi = self.db.execute_query(query_distribusi, fetch=True)
        if df_distribusi is not None:
            if not df_distribusi.empty:
                df_distribusi['Total Distribusi'] = df_distribusi['Total Distribusi'].apply(
                    lambda x: f"Rp {x:,.2f}" if pd.notnull(x) else "Rp 0"
                )
            self.display_table(df_distribusi, "Distribusi Zakat")

    def main_menu(self):
        """Menampilkan menu utama"""
        while True:
            print("\n" + "="*50)
            print(" SISTEM MANAJEMEN ZAKAT ".center(50))
            print("="*50)
            print("1. Tambah Data Muzakki")
            print("2. Lihat Data Muzakki")
            print("3. Laporan Zakat")
            print("4. Keluar")
            
            choice = input("Pilih menu (1-4): ").strip()
            
            if choice == "1":
                self.tambah_muzakki()
            elif choice == "2":
                self.lihat_muzakki()
            elif choice == "3":
                self.laporan_zakat()
            elif choice == "4":
                print("\n👋 Terima kasih telah menggunakan aplikasi.")
                break
            else:
                print("❌ Pilihan tidak valid, silakan coba lagi")
            
            input("\nTekan Enter untuk kembali ke menu...")
        
        self.db.close()

if __name__ == "__main__":
    # Cek dependensi
    try:
        import mysql.connector
        import pandas as pd
        from tabulate import tabulate
    except ImportError as e:
        print("\n❌ Modul yang diperlukan tidak terinstall!")
        print("Silakan install dengan perintah berikut:")
        print("pip install mysql-connector-python pandas tabulate")
        sys.exit(1)
    
    app = ZakatApp()