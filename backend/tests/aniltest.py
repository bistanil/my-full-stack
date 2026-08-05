from app.services.downloader.yahoo import YahooDownloader

df = YahooDownloader.download_stock_history("HAL")

print(df.head())