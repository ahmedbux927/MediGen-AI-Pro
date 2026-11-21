# Photo se list parhne ke liye Tesseract (OCR) install karein

Ye ek baar ka kaam hai. Iske baad MediGen list ki photo (camera ya gallery se) aur scanned PDF parh sakta hai.
Prescription photo wala feature bhi isi program ko use karta hai.

## Steps (shop PC par, Windows)

1. Browser mein search karein: **tesseract ocr windows installer UB Mannheim**
   (ye Windows ke liye Tesseract ka installer hai). Latest "64 bit" installer download karein.
2. Installer chalayein. Default folder hi rehne dein:
   `C:\Program Files\Tesseract-OCR`
3. Language ke option mein **English** ko tick rakhein (default).
4. Install hone ke baad MediGen band karke dobara chalayein.
5. Check karein: Products (ya Medicines) page par **Camera photo** dabayein aur kisi list ki photo lein.
   Agar message aaye "this computer needs the free OCR program", to install path check karein.

## Agar Tesseract kisi aur folder mein install hua hai

`.env` file mein ye line likhein (path apne hisaab se):

    TESSERACT_CMD=D:\Tools\Tesseract-OCR\tesseract.exe

Phir MediGen dobara chalayein.

## Tips for a good photo
- List ko seedha upar se lein, tilt na karein.
- Roshni achhi ho, parchi par saaya na ho.
- Sirf list wala hissa frame mein rakhein.
- Photo 5 MB se choti ho.

## Agar Tesseract install na ho sake
CSV ya PDF se import karein. Ye bina kisi extra program ke chalta hai.
