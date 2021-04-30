from datetime import datetime
from time import sleep
from urllib import parse as urlparse
import pytz
import asyncio
import aiohttp
import json
import re

pnienv = "qa1"
# domainName = "local-qa.staples.com"
domainName = "qe101.staples.com"
applicationPath = "/services/printing"
# authCookieName = "SPLUS.Phoenix.Site.Auth"
authCookieName = "SPLUS.Phoenix.Site.Staging-Prod.Auth"
authCookieValue = "CfDJ8O9Q0PpvA_BJszQq-wRngAWjCIfWdg-0Fq5Mozv3pgZakBuChKUQCpR_tdKjOoAnmSMkEUqO-Nif18ppUlS" + \
                  "QKQyj3H22qpTg9FyPf5mVEcAdRfIfJErRmbqmYPJqT_p8fXwViRACPvqwr-WhCaGEXTHaljpYqlFoxqCWvNMAzXl" + \
                  "Pj0St5AlUF4KOUQvgkt_gLKbKtpWoXKQ5gXHTeB6Gb_5jzBdfR55FuEN_-RFHyAvF2DHysIDQSwTRsDBW69_C0Pu" + \
                  "W306ZHagl8-P1qo66Jx_oLxbeEU75BtmRkjjZYBM5QM4Gg7VUjJnePHUFJmHVdMjQy8cgDTbchLn2ex3Ub78"
# productKey = "337c731e2cc14900"
# productKey = "880e9a0b0a627f97"
# productKey = "550f7cadad98fe98"
# productKey = "34a92d9f78cb90a4"
productKey = "fadb30ec37bdebc8" # same day poster mega staging
# productKey = "b904ce0e33e714d7"  # same day poster
selectedQuantity = 2
seattleStore = "1312"


async def loadCartPage(session, stress):
    async with session.get(f"https://{domainName}{applicationPath}/Cart", ssl=False, timeout=None) as response:
        data = await response.text()
        if stress is True:
            sleep(0.1)
            return None

        userIdPart = re.findall(
            "set_encUserID\('.*'\)", data)[0]
        encUserId = re.split("'", userIdPart)[1]
        sleep(0.1)
        async with session.get(f"https://{domainName}{applicationPath}/services/printing/Cart/Api/GetCartCount",
                               ssl=False, timeout=None) as cartCount:
            await cartCount.text()
        async with session.post(
                f"https://{domainName}{applicationPath}/PC.WebServices/CartService.svc/GetCartItemCounts",
                json={"encUserID": encUserId}, ssl=False, timeout=None) as apiResponse:
            data = await apiResponse.text()
        sleep(0.1)
    return None


async def addToShoppingCart(session, groupKey, projectKey):
    data = {
        "GroupProjectKey": groupKey,
        "Projects": [
            {
                "ProjectKey": projectKey,
                "Quantity": selectedQuantity
            }
        ]
    }
    async with session.post(f"https://{domainName}{applicationPath}/api/v3/cart/AddGroupProjectToCart",
                            json=data, ssl=False, timeout=None) as response:
        await response.text()
    sleep(0.1)
    return None


async def updateProject(session, projectKey):
    async with session.get(f"https://{domainName}{applicationPath}/api/v3/project/activeOptions/{projectKey}",
                           ssl=False, timeout=None) as optionResponse:
        selectedOptions = json.loads(await optionResponse.text())

    selectedOptions["IsCourierDelivery"] = "True"
    data = {
        "ProjectId": projectKey,
        "ProductKey": productKey,
        "SelectedOptions": selectedOptions,
        "SelectedQuantity": selectedQuantity
    }

    async with session.post(f"https://{domainName}{applicationPath}/api/v3/project/UpdateForReview/{projectKey}",
                            json=data, ssl=False, timeout=None) as response:
        await response.text()
    sleep(0.1)
    return response.status


async def estimateShipMethods(session):
    tz = pytz.timezone("America/Los_Angeles")
    now = urlparse.quote(tz.localize(
        datetime.now()).isoformat(timespec="seconds"))
    url = f"https://{domainName}{applicationPath}/cart/api/ShippingMethods/Estimate?retailerProductSku=PNI_PostCards&quantity=100&price=45.99&orderDate={now}"
    async with session.get(url, ssl=False, timeout=None) as response:
        await response.text()
    sleep(0.05)
    return None


async def setShipMethod(session):
    async with session.post(f"https://{domainName}{applicationPath}/cart/api/ShippingMethod",
                            json={"Id": "1tJHqTB,glCJdT3MYpet5WpqwOARm9GXE"}, ssl=False, timeout=None) as response:
        await response.text()
    sleep(0.1)
    return None


async def setPickupLocation(session):
    async with session.post(f"https://{domainName}{applicationPath}/cart/api/PickupLocation",
                            json={"RetailerStoreId": seattleStore}, ssl=False, timeout=None) as response:
        await response.text()
        sleep(0.1)
        return None


async def getStorePromisedTime(session, isExress):
    body = {"Products": [{"ProductSku": "PNI_PostCards_SameDay", "Options": [
        {"Key": "IsExpress", "Value": f"{isExress}"}]}], "RetailerStoreId": "0126"}
    async with session.post(f"https://{domainName}{applicationPath}/cart/api/StorePromiseTime", json=body, ssl=False,
                            timeout=None) as response:
        await response.text()
    sleep(0.05)
    return None


async def loadUpsellPage(session, projectKey):
    async with session.get(f"https://{domainName}{applicationPath}/cart/api/Info", ssl=False, timeout=None) as cartInfo:
        await cartInfo.text()
    async with session.get(
            f"https://{domainName}{applicationPath}/legacy/StoreLocatorProxy/GetDefaultStore?latitude=47.65&longitude=-122.31&locale=en_US",
            ssl=False, timeout=None) as defaultStore:
        await defaultStore.text()
    await estimateShipMethods(session)
    await getStorePromisedTime(session, True)
    await getStorePromisedTime(session, False)
    sleep(0.1)
    return None


async def navigateToCartPage(session, projectGroupKey, projectKey, inStorePickup):
    status = await updateProject(session, projectKey)
    if status < 300:
        if inStorePickup:
            await setPickupLocation(session)
        else:
            await setShipMethod(session)
        await addToShoppingCart(session, projectGroupKey, projectKey)
    return None


async def approveProject(session, projectKey):
    async with session.post(f"https://{domainName}{applicationPath}/api/v3/project/Approve/{projectKey}",
                            json={}, ssl=False, timeout=None) as response:
        await response.text()
    sleep(0.1)
    return None


async def getProjectInfo(session):
    async with session.get(f"https://{domainName}{applicationPath}/product/{productKey}/builder/", ssl=False,
                           timeout=None) as response:
        data = await response.text()
        groupId = re.findall("[0-9]+", response.url.path)[0]
    sleep(0.1)
    summaryUrl = f"https://{domainName}{applicationPath}/api/builder/v3/project/group/summary/{groupId}"
    async with session.get(summaryUrl, ssl=False, timeout=None) as jsonResponse:
        data = json.loads(await jsonResponse.text())

    return (groupId, data["SubProjects"][0]["ProjectKey"])


async def setupAsRik(session):
    async with session.get(f"https://{domainName}{applicationPath}/legacy/station/6B696F736b5F72696B/126/redirect/",
                           ssl=False, timeout=None) as response:
        await response.text()
    sleep(0.1)
    return None


async def setEnvironment(session):
    async with session.get(f"https://{domainName}{applicationPath}/?pnienv={pnienv}",
                           ssl=False, timeout=None) as response:
        await response.text()
    sleep(0.1)
    return None


async def visitSite():
    cookies = {authCookieName: authCookieValue}
    async with aiohttp.ClientSession(cookies=cookies) as session:
        await setEnvironment(session)
        projectInfo = await getProjectInfo(session)
        await approveProject(session, projectInfo[1])
        await navigateToCartPage(session, projectInfo[0], projectInfo[1], True)


if __name__ == "__main__":
    asyncio.run(visitSite())
