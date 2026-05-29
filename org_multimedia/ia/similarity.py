"""
Sistema de similitud de contenido para el organizador multimedia.
"""

from typing import List, Dict, Tuple
from pathlib import Path
import hashlib
import os


class ContentSimilarity:
    """
    Clase para calcular similitud entre archivos basada en su contenido.
    """
    
    def __init__(self):
        self.cache = {}
    
    def calculate_similarity(self, file1: str, file2: str) -> float:
        """
        Calcula la similitud entre dos archivos.
        
        Args:
            file1 (str): Ruta al primer archivo
            file2 (str): Ruta al segundo archivo
            
        Returns:
            float: Valor de similitud entre 0 y 1
        """
        # Verificar que los archivos existan
        if not Path(file1).exists() or not Path(file2).exists():
            return 0.0
        
        # Crear clave única para el par de archivos
        file_pair = tuple(sorted([file1, file2]))
        
        # Verificar en caché
        if file_pair in self.cache:
            return self.cache[file_pair]
        
        # Calcular similitud basada en hashes
        similarity = self._calculate_hash_similarity(file1, file2)
        
        # Almacenar en caché
        self.cache[file_pair] = similarity
        
        return similarity
    
    def _calculate_hash_similarity(self, file1: str, file2: str) -> float:
        """
        Calcula similitud basada en hashes de archivos.
        """
        try:
            # Calcular hashes de los archivos
            hash1 = self._calculate_file_hash(file1)
            hash2 = self._calculate_file_hash(file2)
            
            # Calcular similitud basada en coincidencia de bits
            return self._calculate_bit_similarity(hash1, hash2)
        except Exception:
            # Si hay error, asumir baja similitud
            return 0.0
    
    def _calculate_file_hash(self, file_path: str) -> str:
        """
        Calcula hash de un archivo.
        """
        hash_md5 = hashlib.md5()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_md5.update(chunk)
        return hash_md5.hexdigest()
    
    def _calculate_bit_similarity(self, hash1: str, hash2: str) -> float:
        """
        Calcula similitud basada en coincidencia de bits entre hashes.
        """
        # Convertir hashes a bits
        bits1 = bin(int(hash1, 16))[2:].zfill(128)
        bits2 = bin(int(hash2, 16))[2:].zfill(128)
        
        # Contar bits iguales
        same_bits = sum(b1 == b2 for b1, b2 in zip(bits1, bits2))
        
        # Calcular porcentaje de similitud
        return same_bits / 128.0
    
    def find_similar_files(self, file_path: str, candidates: List[str], 
                          threshold: float = 0.7) -> List[Tuple[str, float]]:
        """
        Encuentra archivos similares a uno dado.
        
        Args:
            file_path (str): Ruta al archivo de referencia
            candidates (List[str]): Lista de archivos candidatos
            threshold (float): Umbral mínimo de similitud
            
        Returns:
            List[Tuple[str, float]]: Lista de archivos similares y sus valores de similitud
        """
        similar_files = []
        
        for candidate in candidates:
            if Path(candidate).exists():
                similarity = self.calculate_similarity(file_path, candidate)
                if similarity >= threshold:
                    similar_files.append((candidate, similarity))
        
        # Ordenar por similitud descendente
        similar_files.sort(key=lambda x: x[1], reverse=True)
        
        return similar_files
    
    def get_suggestions(self, file_path: str, folder_path: str) -> List[Dict[str, Any]]:
        """
        Obtiene sugerencias de carpetas similares basadas en contenido.
        
        Args:
            file_path (str): Ruta al archivo de referencia
            folder_path (str): Ruta a la carpeta para buscar sugerencias
            
        Returns:
            List[Dict[str, Any]]: Lista de sugerencias
        """
        suggestions = []
        
        # Obtener archivos en la carpeta
        folder = Path(folder_path)
        if not folder.exists():
            return suggestions
            
        # Solo procesar archivos del mismo tipo
        file_extension = Path(file_path).suffix.lower()
        
        # Buscar archivos similares en la carpeta
        for item in folder.iterdir():
            if item.is_file() and item.suffix.lower() == file_extension:
                similarity = self.calculate_similarity(file_path, str(item))
                if similarity > 0.5:  # Umbral de similitud
                    suggestions.append({
                        'file': str(item),
                        'similarity': similarity,
                        'folder': str(folder)
                    })
        
        return suggestions


# Ejemplo de uso
if __name__ == "__main__":
    similarity = ContentSimilarity()
    
    # Ejemplo de uso (requiere archivos reales)
    try:
        # similarity1 = similarity.calculate_similarity('ruta/a/archivo1.jpg', 'ruta/a/archivo2.jpg')
        # print(f"Similitud: {similarity1}")
        pass
    except Exception as e:
        print(f"Error en cálculo de similitud: {e}")
