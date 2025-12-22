# cryptobot_fast.py
import aiohttp
import asyncio
import json
import logging
from datetime import datetime
from typing import Dict, Any, Optional, List

logger = logging.getLogger(__name__)

class CryptoBotTurbo:
    """ТУРБО реализация CryptoBot API на чистом aiohttp"""
    
    def __init__(self, api_key: str, testnet: bool = False):
        self.api_key = api_key
        self.base_url = "https://testnet-pay.crypt.bot" if testnet else "https://pay.crypt.bot"
        self.session = None
        self._lock = asyncio.Lock()
        
    async def _get_session(self):
        """Создает или возвращает сессию"""
        if self.session is None or self.session.closed:
            timeout = aiohttp.ClientTimeout(total=5, connect=2)
            connector = aiohttp.TCPConnector(
                limit=20,
                ttl_dns_cache=300,
                keepalive_timeout=30,
                force_close=False
            )
            self.session = aiohttp.ClientSession(
                timeout=timeout,
                connector=connector,
                headers={
                    "Crypto-Pay-API-Token": self.api_key,
                    "Content-Type": "application/json"
                }
            )
        return self.session
    
    async def _make_request(self, method: str, endpoint: str, data: Optional[Dict] = None) -> Dict:
        """Универсальный метод для запросов"""
        try:
            session = await self._get_session()
            url = f"{self.base_url}/api/{endpoint}"
            
            start_time = datetime.now()
            
            if method.upper() == "GET":
                async with session.get(url, params=data) as response:
                    result = await response.json()
            else:
                async with session.post(url, json=data) as response:
                    result = await response.json()
            
            response_time = (datetime.now() - start_time).total_seconds() * 1000
            
            if response_time > 1000:
                logger.warning(f"Медленный ответ CryptoBot: {response_time:.0f}ms")
            
            return result
            
        except asyncio.TimeoutError:
            logger.error("CryptoBot: Таймаут запроса")
            return {"ok": False, "error": "timeout"}
        except Exception as e:
            logger.error(f"CryptoBot ошибка: {e}")
            return {"ok": False, "error": str(e)}
    
    async def get_me(self):
        """Проверка работы API"""
        return await self._make_request("GET", "getMe")
    
    async def create_invoice(self, amount: float, currency: str = "USDT", **kwargs) -> Dict:
        """Создание счета для пополнения - ОЧЕНЬ БЫСТРО"""
        payload = {
            "asset": currency,
            "amount": str(amount),
            "description": f"Пополнение {amount} {currency} | NOXWAT Casino",
            "hidden_message": "💰 Баланс пополнен автоматически",
            "paid_btn_name": "viewItem",
            "paid_btn_url": "https://t.me/NoxwatCasinoBot",
            "payload": "deposit",
            "allow_comments": False,
            "allow_anonymous": True,
            "expires_in": 1800  # 30 минут
        }
        payload.update(kwargs)
        
        result = await self._make_request("POST", "createInvoice", payload)
        
        if result.get("ok"):
            logger.info(f"✅ Создан счет: {amount} {currency}")
            return {
                "success": True,
                "invoice_id": result["result"]["invoice_id"],
                "pay_url": result["result"]["pay_url"],
                "amount": amount,
                "currency": currency
            }
        else:
            logger.error(f"❌ Ошибка создания счета: {result.get('error')}")
            return {
                "success": False,
                "error": result.get("error", "Unknown error")
            }
    
    async def transfer(self, user_id: int, amount: float, currency: str = "USDT", **kwargs) -> Dict:
        """Вывод средств пользователю - МГНОВЕННО"""
        payload = {
            "user_id": user_id,
            "asset": currency,
            "amount": str(amount),
            "spend_id": f"w_{user_id}_{int(datetime.now().timestamp())}",
            "comment": f"Вывод {amount} {currency} | NOXWAT Casino",
            "disable_send_notification": False
        }
        payload.update(kwargs)
        
        result = await self._make_request("POST", "transfer", payload)
        
        if result.get("ok"):
            logger.info(f"✅ Вывод {amount} {currency} пользователю {user_id}")
            return {
                "success": True,
                "transfer_id": result["result"]["transfer_id"],
                "amount": amount,
                "currency": currency,
                "status": "completed"
            }
        else:
            logger.error(f"❌ Ошибка вывода: {result.get('error')}")
            return {
                "success": False,
                "error": result.get("error", "Unknown error")
            }
    
    async def get_balance(self) -> List[Dict]:
        """Получение баланса"""
        result = await self._make_request("GET", "getBalance")
        
        if result.get("ok"):
            return result["result"]
        return []
    
    async def get_exchange_rates(self) -> List[Dict]:
        """Курсы валют"""
        try:
            result = await self._make_request("GET", "getExchangeRates")
            return result.get("result", []) if result.get("ok") else []
        except:
            # Заглушка если API не работает
            return [
                {"source": "USDT", "target": "RUB", "rate": 90.0},
                {"source": "USDT", "target": "USD", "rate": 1.0}
            ]
    
    async def close(self):
        """Закрытие сессии"""
        if self.session and not self.session.closed:
            await self.session.close()
    
    async def __aenter__(self):
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()

# Система очереди для быстрых выплат
class PaymentQueue:
    """Очередь выплат для избежания конфликтов"""
    
    def __init__(self):
        self.queue = asyncio.Queue()
        self.processing = set()
        self._running = True
        
    async def add_payment(self, user_id: int, amount: float, currency: str = "USDT"):
        """Добавление выплаты в очередь"""
        await self.queue.put({
            "user_id": user_id,
            "amount": amount,
            "currency": currency,
            "timestamp": datetime.now()
        })
    
    async def process_payments(self, cryptobot: CryptoBotTurbo):
        """Обработка очереди выплат"""
        while self._running:
            try:
                payment = await asyncio.wait_for(self.queue.get(), timeout=1.0)
                
                if payment["user_id"] in self.processing:
                    # Уже обрабатывается
                    continue
                
                self.processing.add(payment["user_id"])
                
                try:
                    result = await cryptobot.transfer(
                        payment["user_id"],
                        payment["amount"],
                        payment["currency"]
                    )
                    
                    if result["success"]:
                        logger.info(f"✅ Выплата {payment['amount']} {payment['currency']} пользователю {payment['user_id']}")
                    else:
                        logger.error(f"❌ Ошибка выплаты: {result.get('error')}")
                        # Возвращаем в очередь при ошибке
                        await asyncio.sleep(5)
                        await self.queue.put(payment)
                        
                except Exception as e:
                    logger.error(f"❌ Критическая ошибка выплаты: {e}")
                    
                finally:
                    self.processing.remove(payment["user_id"])
                    
            except asyncio.TimeoutError:
                continue
            except Exception as e:
                logger.error(f"❌ Ошибка обработки очереди: {e}")
                await asyncio.sleep(1)
    
    def stop(self):
        """Остановка обработки"""
        self._running = False