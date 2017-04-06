# Write-Up do zadania Starblind z Teaser Confidence CTF

Zadanie: Starblind [link do zadania](https://s3.eu-central-1.amazonaws.com/dragonsector2-ctf-prod/starblind_96bbc884beb953bee0f120d0994d30d6073c53afd582f456586d7effa184dc25/starblind.html)

Write-up: **Artur Nowak**

1. **Start**. Po uruchomieniu zadania widzimy znak zachęty, wpisujemy dowolny ciąg znaków i po dojściu do 27 znaków sprawdzana jest poprawność hasła, to oczywiście daje nam już podpowiedź, że hasło ma właśnie taką długość.


  ![alt tag](https://github.com/nowakartur/StarblindCTF/raw/master/img/1.PNG)


2. **Kod strony.** Okazuje się, że kod strony został zaciemniony. 
    
  ![alt tag](https://github.com/nowakartur/StarblindCTF/raw/master/img/2.PNG)

  Ukrycie go w base64 nie przysparza jednak żadnych kłopotów, przeglądarka i tak musi go rozkodować żeby użyć, więc albo zapisujemy źródło strony i dekodujemy na boku, albo od razu sięgamy w narzędziach developerskich przeglądarki do zdekodowanego javascriptu.
  
  ![alt tag](https://github.com/nowakartur/StarblindCTF/raw/master/img/3.PNG)

3. **Test lokalnej kopii strony**. Dla wygody kopiujemy sobie stronę na dysk i podmieniamy zakodowaną część javascriptu na zewnętrznie linkowany osobny plik `javascript.js` w którym możemy dowolnie modyfikować kod. 
	
    Niestety po tej operacji strona uruchamiana lokalnie przestała działać i w konsoli JS widzimy:

    ```
    Uncaught TypeError: Cannot read property 'parentNode' of null
        at HandleOnLoad (javascript.js:677)
        at checker (javascript.js:1063)
    ```

	być może to kolejne zabezpieczenie lub po prostu przypadek (jest to zupełnie nieistotne dla rozwiązania zadania). Linie powodujące wspomniany błąd:
    
    ```
    let removeMe = document.getElementById('removeme');
    removeMe.parentNode.removeChild(removeMe);
    ```
    nie wydają się ważne (usuwają tylko komunikat o niewspieranej przeglądarce). Po ich zakomentowaniu strona działa lokalnie i możemy przejść do edycji źródeł.

4. **CheckPassword**. Tuż pod liniami które zakomentowaliśmy widzimy:
    ```javascript
    var HandleDown = function(e) {
      const code = e.key.charCodeAt(0);
      if (e.key.length === 1 && code >= 0x20 && code <= 0x7e) {
        if (gPassword.length < 27) {
          gPassword += e.key;
        }
    
      } else if (e.key === "Backspace") {
        gPassword = gPassword.substring(0, gPassword.length - 1);
        e.preventDefault();
      } else {
        //console.log(e);
      }
    
      if (gLastChecked != gPassword) {
        gLastChecked = gPassword;
        CheckPassword();
      }
    };
    ```
    a więc faktycznie skrypt szuka 27 znakowego hasła: `if (gPassword.length < 27) {`  i robi to w funkcji `CheckPassword();`

	W funkcji `CheckPassword`:
    
    ```javascript
    var CheckPassword = function() {
  	if (gPassword.length != 27) {
    	gGoodPassword = false;
    	return;
  	}

  	const hash = CalcSHA4(gPassword);
  	const correct = "983bb35ed0a800fcc85d12806df9225364713be578ba67f65bc508b77f0c54878eda18a5eed50bac705bdc7db205623221e8ffe330483955a22216960754a122";
  	gGoodPassword = hash === correct;
	};
    ```
    znów znajdujemy zabezpieczenie długości hasła `if (gPassword.length != 27) {` , ale ważniejsze jest, że po obliczeniu funkcją `CalcSHA4` hasha z hasła powinniśmy otrzymać niżej podany wynik:
    ```javascript
    const correct = "983bb35ed0a800fcc85d12806df9225364713be578ba67f65bc508b77f0c54878eda18a5eed50bac705bdc7db205623221e8ffe330483955a22216960754a122";
    ```
    
5. **CalcSHA4**. Widać, że funkcja `CalcSHA4` to nasz główny wektor ataku więc zajmujemy jej analizą.
	
    Pierwsza faza uzupełnia pierwsze 27 elementów 64 elementowej tablicy kodami ascii wpisanego hasła:
    
    ```javascript
    for (let i = 0; i < block.length; i++) {
        r[i] = block.charCodeAt(i);
    }
    ```

    następnie elementy od 32 do 63 wypełniane są wartościami niezwiązanymi z hasłem. Typowe zachowanie blokowych funkcji szyfrujących, które muszą umieć operować na danych o długościach niebędących wielokrotnością rozmiaru bloku.

    ```javascript
    for (let i = 32; i < 64; i++) {
        r[i] = i * 48271;
    }
    ```

    Definiowane są dwie funkcje używane później: `Xor` i `Perm`.  Jeśli ich nazwy będą odpowiadały tym co robią to jest to kolejny przykład na sugerowanie się autora budową szyfrów / funkcji skrótu. Obecnie używane algorytmy używają na przemian między innymi takich właśnie funkcji tworząc z nich rundy kodujące.

    Po definicji funkcji widać 512 ich wywołań na przemian (każde wywołanie z innym kluczem mieszającym, dla `XOR` 64 elementowym, dla `PERM` 512 elementowym)

    W tej chwili wyraźnie już widać, że musimy odwrócić działanie funkcji `CalcSHA4` aby poznać jakie dane wejściowe wygenerują nam oczekiwany wynik równy stałej `correct`


6. **Odwracanie działania funkcji CalcSHA4**
  
    Na pierwszy rzut oka widać, że funkcja `XOR` robi dokładnie to co sugeruje jej nazwa (można sobie wyobrazić, że częścią obfuskacji kodu będzie nazwanie funkcji w sposób sugerujący, że robi prostego XOR tak naprawdę robiąc coś innego - tutaj taka sytuacja nie występuje), a więc biorąc pod uwagę, że podwójne (i każde parzyste) wywołanie XOR na jakichkolwiek danych wróci do pierwotnej postaci tych danych to funkcją `XOR` nie musimy się zajmować.

	Jako, że nie mam doświadczenia w zadaniach CTF, uznałem że potrzebujemy zejść jak najniżej z poziomem skomplikowania zadania. Tworzymy nowy plik, który będzie miał tylko jedno wywołanie funkcji `PERM` i jedno wywołanie funkcji odwrotnegj do `PERM` - nazwijmy ją `DEPERM`. Będziemy starać się najmniejszą możliwą paczkę danych przepuścić kolejno przez `PERM` i `DEPERM' - jeśli w wyniku otrzymamy dane wejściowe - będziemy krok dalej.

	Tworzymy plik `deperm.html` zawierający tylko niezbędne elementy, czyli funkcje `PERM`, `DEPERM` i wywołanie powyższych na przykładowych danych. Okazuje się, że musimy do naszego pliku dołączyć zdefiniowaną w kodzie zadania funkcję `Math.sgn` (funkcja ta zwraca `true` lub `false` w zależności od znaku przekazanego parametru - choć sama implementacja jest dość podejrzana funkcję kopiujemy).

	```javascript
	Math.sgn = function(a) { return 1/a<0;};
	```

	    
	**Różnice między PERM a DEPERM:**
	* funkcja `DEPERM` musi iterować w przeciwną stronę co funkcja `PERM`, musimy wykonywać wszystko odwrotnie, stąd: `for (let i = 511; i >= 0; i--) {`
	* w samej części obliczającej zmieniamy `src_byte` i `src_bit` na `dst_byte` i `dst_bit`

	Żadnej innej operacji nie musimy zmieniać.
  
      ```javascript
    let deperm = function (imm) {
      let n = new Uint8Array(64);
      for (let i = 511; i >= 0; i--) {
        const dst_bit = i%8;
        const dst_byte = i/8|0;
        const sign = Math.sgn(imm[i]);
        const idx = sign ? -imm[i] : imm[i];
        const src_bit = idx%8;
        const src_byte = idx/8|0;
       
        if (i < 3) {
          console.log(i + " :src byte/bit: " +  src_byte + "/" + src_bit + " | dst byte/bit: " + dst_byte + "/" + dst_bit + " | idx: " + idx + " | imm: " + imm[i]);
        }
        let b = (r[dst_byte] >> dst_bit) & 1;
        if (sign) { b ^= 1; }
        n[src_byte] |= b << src_bit;
      }
      r = n;
    };  
    ```
  
    Po sprawdzeniu działania widać, że funkcja odwrotna do `PERM` przywraca oryginalną zawartość tablicy `r`. Dla przejrzystości pokazano tylko po 3 mieszania dla każdej z funkcji (trzy pierwsze dla `PERM` i trzy ostatnie dla `DEPERM`):
  
  
  ![alt tag](https://github.com/nowakartur/StarblindCTF/raw/master/img/5.PNG)
  

7. **Mamy wszystko ? Składamy całość.**

	Tworzymy plik `decrypt.html`:
    
    Funkcja `PERM` zostaje zamieniona na jej odwrotność `DEPERM` przetestowaną w poprzednim kroku.
	
    Wszystkie wywołania funkcji `PERM` i `XOR` zamieniamy w kolejności (wykonujemy od ostatniego do pierwszego). Możemy do tego użyć szybkiego skryptu w pythonie:
    
    ```python
    f = open('commands.txt', 'r')
	lines = f.readlines()

	w = open('backwards.txt','w')
	for i in range(511,-1,-1):
    	w.write(lines[i])
    	print(i)

    ```
    
	Hash ze zmiennej `correct` zmieniamy na tablicę uint'ów (postać jaką ma tablica `r`) i wstrzykujemy ją w odpowiednie miejsce:
    
    ```javascript
    r = [152, 59, 179, 94, 208, 168, 0, 252, 200, 93, 18, 128, 109, 249, 34, 83, 100, 113, 59, 229, 120, 186, 103, 246, 91, 197, 8, 183, 127, 12, 84, 135, 142, 218, 24, 165, 238, 213, 11, 172, 112, 91, 220, 125, 178, 5, 98, 50, 33, 232, 255, 227, 48, 72, 57, 85, 162, 34, 22, 150, 7, 84, 161, 34]

    ```

	Po 512 rundach naprzemiennych `XOR` i `DEPERM` wyciągamy zawartość tabeli `r` jaką ma po 512 rundach i wrzucamy 27 pierwszych jej elementów do pythona (zmieniając kody ASCII na znaki) otrzymując flagę:

	```
	Python 3.6.0 (v3.6.0:41df79263a11, Dec 23 2016, 07:18:10) [MSC v.1900 32 bit (Intel)] on win32

	>>> r = [68, 114, 103, 110, 83, 123, 72, 117, 109, 97, 110, 107, 49, 110, 100, 69, 109, 112, 105, 114, 101, 48, 102, 65, 98, 104, 125, 0, 0, 0, 0, 0, 224, 111, 254, 141, 28, 171, 58, 201, 88, 231, 118, 5, 148, 35, 178, 65, 208, 95, 238, 125, 12, 155, 42, 185, 72, 215, 102, 245, 132, 19, 162, 49]

	>>> print([chr(x) for x in r[:27]])
	['D', 'r', 'g', 'n', 'S', '{', 'H', 'u', 'm', 'a', 'n', 'k', '1', 'n', 'd', 'E', 'm', 'p', 'i', 'r', 'e', '0', 'f', 'A', 'b', 'h', '}']

	```

	Sprawdzamy flagę na oryginalnej stronie i działa !!

![alt tag](https://github.com/nowakartur/StarblindCTF/raw/master/img/6.PNG)
