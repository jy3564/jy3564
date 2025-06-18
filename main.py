# region imports
from datetime import datetime
from AlgorithmImports import *
from alpha import custom_alpha

# endregion


class CompetitionAlgorithm(QCAlgorithm):
    
    def Initialize(self):

        # Backtest parameters
        self.SetStartDate(2024, 8, 1)
        self.SetEndDate(2024, 12, 1)
        self.SetCash(1000000)
        self.SetWarmUp(timedelta(days=30))

        # Parameters:
        self.final_universe_size = 400

        # Universe selection
        self.rebalanceTime = self.time
        self.universe_type = "equity"

        if self.universe_type == "equity":
            self.Log("adding equitiy universe")
            self.add_universe(self.equity_filter)
            #self.add_universe(CryptoUniverse.coinbase(self._crypto_universe_filter))

        self.UniverseSettings.Resolution = Resolution.Hour

        self.set_portfolio_construction(self.MyPCM())
        self.set_alpha(custom_alpha(self))
        self.set_execution(VolumeWeightedAveragePriceExecutionModel())
        self.add_risk_management(NullRiskManagementModel())
 
        # set account type
        #self.SetBrokerageModel(BrokerageName.InteractiveBrokersBrokerage, AccountType.Margin)

    def _crypto_universe_filter(self, data):
        if self.Time <= self.rebalanceTime:
            return self.Universe.Unchanged
        self.rebalanceTime = self.Time + timedelta(days=300)
        # Define the universe selection function
        sorted_by_vol = sorted(data, key=lambda x: x.volume_in_usd, reverse=True)[:30]
        first_of_tickers_added = ['']
        new_universe = []
        for cf in sorted_by_vol:
            # remove USD and EUR from string
            sym_string = str(cf.symbol).replace("USDT", "").replace("USDC", "").replace("USD", "")\
                .replace("EUR", "").replace("GBP", "").split(" ")[0]
            self.Log("sym_string: " + sym_string)
            if sym_string not in first_of_tickers_added:
                first_of_tickers_added.append(sym_string)
                new_universe.append(cf)
        sorted_by_vol = sorted(new_universe, key=lambda x: x.volume_in_usd, reverse=True)
        final =  [cf.symbol for cf in sorted_by_vol][:10]
        self.Log("final: ")
        for i in final:
            self.Log(str(i))
        return final

        
    def equity_filter(self, data):
        self.Log("in filter for equities")
        # Rebalancing monthly
        if self.Time <= self.rebalanceTime:
            return self.Universe.Unchanged
        self.rebalanceTime = self.Time + timedelta(days=300)
        
        sortedByDollarVolume = sorted(data, key=lambda x: x.DollarVolume, reverse=True)
        final = [x.Symbol for x in sortedByDollarVolume if x.HasFundamentalData and x.price > 10 and x.MarketCap > 2000000000][:self.final_universe_size]
        self.Log("coming out of course: " + str(len(final)))
        return final
    class MyPCM(InsightWeightingPortfolioConstructionModel): 
        # override to set leverage higher
        def CreateTargets(self, algorithm, insights): 
            targets = super().CreateTargets(algorithm, insights) 
            return [PortfolioTarget(x.Symbol, x.Quantity * 1.85) for x in targets]
        



        
        



    








            

            

     