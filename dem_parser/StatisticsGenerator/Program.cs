using System;
using System.Reflection;
using System.IO;
using DemoInfo;
using System.Collections.Generic;
using System.Linq;
using System.Text;
using System.Threading.Tasks;

namespace StatisticsGenerator
{
    public class MainClass
    {
        public static List<String> finished;
        public static void Main(string[] args)
        {
            if (args.Length == 0)
            {
                args = new string[] { @"C:\Users\Artem\Documents\demos" };
            }
            var directory = new DirectoryInfo(args[0]);
            finished = File.ReadLines("finished.txt").Select(x => x.Split('\\').Last())
                .Select(x =>
                {
                    var indexOfDemDot = x.IndexOf(".dem");
                    x =  x.Substring(0, indexOfDemDot + ".dem".Length);
                    return x;
                }).ToList();
            
            var allDemoFiles = directory.GetFiles("*.dem", SearchOption.AllDirectories);

            var toProcess = allDemoFiles.Where(x => !finished.Contains(x.Name)).ToList();
            Parallel.ForEach(
                toProcess,
                new ParallelOptions {  MaxDegreeOfParallelism = 8 },
                demoFileInfo => GenerateReport(demoFileInfo));

            Console.WriteLine("Completed");

        }
        public static void GenerateReport(FileInfo demoInfo)
        {
            var fileName = demoInfo.FullName;
            using (var fileStream = File.OpenRead(fileName))
            {
                using (var parser = new DemoParser(fileStream))
                {
                    List<bool> RoundWins = new List<bool>();
                    parser.ParseHeader();
                    string map = parser.Map;
                    string outputFileName = fileName + "." + map + ".csv";

                    if (File.Exists(outputFileName))
                        File.Delete(outputFileName);
                    var outputStream = new StreamWriter(outputFileName)
                    {
                        AutoFlush = true
                    };

                    outputStream.WriteLine(GenerateCSVHeader());

                    bool hasMatchStarted = false;
                    int currentRound = 0;

                    int ctStartroundMoney = 0, tStartroundMoney = 0, ctEquipValue = 0, ctSaveAmount = 0, tSaveAmount = 0;


                    int defuses = 0;
                    int plants = 0;

                    List<Player> ingame = new List<Player>();
                    List<PlayerStatsOnBombplant> playerStatsAfterPlant = new List<PlayerStatsOnBombplant>();
                    List<EquipmentClass> terroristWeaponsAfterPlant = new List<EquipmentClass>();
                    Dictionary<int, Tuple<int, int>> playerKdRatios = new Dictionary<int, Tuple<int, int>>();

                    bool bombPlanted = false;
                    bool ctWinAfterBombPlant = false;
                    int ctTeamScoreAfterBombPlant = 0;
                    int tAliveCount = 0;
                    var bombPlantSite = "";


                    parser.MatchStarted += (sender, e) =>
                    {
                        hasMatchStarted = true;

                        ingame.AddRange(parser.PlayingParticipants);
                        currentRound = 0;
                    };

                    parser.RoundStart += (sender, e) =>
                    {
                        if (!hasMatchStarted)
                            return;
                        currentRound++;

                        if (bombPlanted)
                        {

                            ctTeamScoreAfterBombPlant = parser.CTScore;

                            //How much money had each team at the start of the round?
                            ctStartroundMoney = parser.Participants.Where(a => a.Team == Team.CounterTerrorist).Sum(a => a.Money);
                            tStartroundMoney = parser.Participants.Where(a => a.Team == Team.Terrorist).Sum(a => a.Money);
                            var ctTeamName =   parser.Participants.FirstOrDefault(a => a.Team == Team.CounterTerrorist)?.AdditionaInformations?.Clantag;
                            var tTeamName = parser.Participants.FirstOrDefault(a => a.Team == Team.Terrorist)?.AdditionaInformations?.Clantag;

                            //And how much they did they save from the last round?
                            ctSaveAmount = parser.Participants.Where(a => a.Team == Team.CounterTerrorist && a.IsAlive).Sum(a => a.CurrentEquipmentValue);
                            tSaveAmount = parser.Participants.Where(a => a.Team == Team.Terrorist && a.IsAlive).Sum(a => a.CurrentEquipmentValue);

                            PrintRoundResults(parser, outputStream, ctTeamName, tTeamName, currentRound, parser.CTScore, parser.TScore,
                                playerStatsAfterPlant.Where(x => x.IsAlive).Count(), tAliveCount, bombPlantSite, playerStatsAfterPlant, terroristWeaponsAfterPlant, ctWinAfterBombPlant);
                        }

                        bombPlanted = false;
                        ctWinAfterBombPlant = false;
                        tAliveCount = 0;
                        bombPlantSite = "";
                        playerStatsAfterPlant.Clear();
                    };

                    parser.BombPlanted += (sender, e) =>
                    {
                        if (!hasMatchStarted)
                            return;

                        plants++;
                        bombPlanted = true;

                        var bombPosition = e.Player.Position;
                        bombPlantSite = e.Site.ToString();

                        ctEquipValue = parser.Participants.Where(a => a.Team == Team.CounterTerrorist).Sum(a => a.CurrentEquipmentValue);
                        tAliveCount = parser.Participants.Where(a => a.Team == Team.Terrorist).Count(a => a.IsAlive);

                        playerStatsAfterPlant = parser.Participants.Where(a => a.Team == Team.CounterTerrorist).Select(x => new PlayerStatsOnBombplant(x)
                        {
                            DistanceToPlant = VectorDistance(x.Position, bombPosition)
                        }).ToList();

                        terroristWeaponsAfterPlant = parser.Participants.Where(a => a.Team == Team.Terrorist).Select(x => GetMainWeaponClassOfPlayer(x.Weapons)).ToList();

                        ctTeamScoreAfterBombPlant = parser.CTScore;
                    };

                    parser.BombDefused += (sender, e) =>
                    {
                        if (!hasMatchStarted)
                            return;

                        defuses++;
                        ctWinAfterBombPlant = true;
                    };

                    parser.ParseToEnd();
               
                    outputStream.Close();
                    Console.WriteLine("Finished demo " + fileName);
                }
            }
        }
        static bool ShouldTryToDefuse(DemoParser parser)
        {
            var currentRound = parser.CTScore + parser.TScore;

            if (currentRound < 30)
            {
                var pistolRound = currentRound == 0 || currentRound == 15;
                var lastRoundBeforeLose = currentRound < 30 && parser.TScore == 15 && parser.CTScore <= 14;
                return !(pistolRound || lastRoundBeforeLose || currentRound == 15);
            }
            else
            {
                var isLastRoundInDiff = (parser.TScore - parser.CTScore) == 3;
                var lastRoundBeforeSwitch = ((currentRound - 30) % 3) == 0;
                return isLastRoundInDiff || lastRoundBeforeSwitch;
            }
        }

        static int GetLoseBonus(DemoParser parser, int previousTimeLosed)
        {
            return 1400 + Math.Min(4, previousTimeLosed) * 500;
        }

        static string GenerateCSVHeader()
        {
            var features = $"{"Map"};" +
                $"{"Round-Number"};" +
                $"{"CT-Score"};" +
                $"{"T-Score"};" +
                $"{"CT-Alive"};" +
                $"{"T-Alive"};" +
                $"{"BombPlantSite"};";
            //$"{"LoseBonus"};";

            const int teamSize = 5;
            for (int i = 0; i < teamSize; i++)
            {
                features += $"player{i}-Alive;" +
                $"player{i}-Gun;" +
                $"player{i}-EquipValue;" +
                $"player{i}-HEGrenade;" +
                $"player{i}-Smoke;" +
                $"player{i}-Flash;" +
                //$"player{i}-KDRation;" +
                $"player{i}-DistancetoPlant;" +
                $"player{i}-Armor;" +
                $"player{i}-HasHelmet;" +
                $"player{i}-HP;" +
                $"player{i}-DefuseKit;";
            }

            for (int i = 0; i < teamSize; i++)
            {
                features += $"TPlayer{i}_WeaponClass;";
            }

            features += $"CT-Win";
     
            return features;
        }

        static void PrintRoundResults(DemoParser parser, StreamWriter outputStream,
            string tTeam,
            string ctTeam,
            int roundNumber,
            int currentCtScore, int currentTScore,
            int ctAliveCount, int tAliveCount,
            string bombPlantSite, //int loseBonus,
            List<PlayerStatsOnBombplant> ctPlayerStats,
            List<EquipmentClass> tPlayersEquipment,
            bool ctWinAfterBombPlant)
        {
            var resString = string.Empty;
            resString += $"{parser.Map};";
            resString += $"{roundNumber};";
            resString += $"{currentCtScore};";
            resString += $"{currentTScore};";
            resString += $"{ctAliveCount};";
            resString += $"{tAliveCount};";
            resString += $"{bombPlantSite};";
            //resString += $"{loseBonus};";

            foreach (var player in ctPlayerStats)
            {
                resString += $"{player.IsAlive};";
                resString += $"{player.MainWeapon};";
                resString += $"{player.CurrentEquipmentValue};";

                resString += $"{player.HasHE};";
                resString += $"{player.HasSmoke};";
                resString += $"{player.HasFlash};";

                resString += $"{player.DistanceToPlant};";

                resString += $"{player.Armor};";
                resString += $"{player.HasHelmet};";

                resString += $"{player.HP};";
                resString += $"{player.DefuseKit};";
            }

            foreach (var equipmentClass in tPlayersEquipment)
            {
                resString += $"{equipmentClass};";
            }

            resString += $"{ctWinAfterBombPlant}";

            outputStream.WriteLine(resString);
        }

        static EquipmentClass GetMainWeaponClassOfPlayer(IEnumerable<Equipment> equipment)
        {
            return equipment.Where(x => (int)x.Class <= 4 && (x.ReserveAmmo + x.AmmoInMagazine) > 0).OrderByDescending(x => x.Class)
                .FirstOrDefault()?.Class ?? EquipmentClass.Unknown;
        }

        public class PlayerStatsOnBombplant
        {
            public Player Player { get; set; }

            private IEnumerable<Equipment> grenades;

            public PlayerStatsOnBombplant(Player player)
            {
                this.Player = player;
                grenades = player.Weapons.Where(x => x.Class == EquipmentClass.Grenade);

                this.HasSmoke = grenades.Any(x => x.Weapon == EquipmentElement.Smoke);
                this.HasHE = grenades.Any(x => x.Weapon == EquipmentElement.HE);
                this.HasFlash = grenades.Any(x => x.Weapon == EquipmentElement.Flash);

                Armor = player.Armor;
                HP = player.HP;
                CurrentEquipmentValue = player.CurrentEquipmentValue;
                IsAlive = player.IsAlive;
                MainWeapon = GetMainWeaponClassOfPlayer(player.Weapons);
                HasHelmet = player.HasHelmet;
                DefuseKit = player.HasDefuseKit;

            }
            public bool IsAlive { get; set; }
            public bool HasSmoke { get; set; }
            public bool HasHE { get; set; }
            public bool HasFlash { get; set; }
            public int Armor { get; set; }
            public int HP { get; private set; }
            public int CurrentEquipmentValue { get; private set; }
            public double DistanceToPlant { get; set; }
            public EquipmentClass MainWeapon { get; set; }
            public bool HasHelmet { get; }
            public bool DefuseKit { get; set; }
        }

        public static double VectorDistance(Vector v1, Vector v2)
        {
            return Math.Sqrt(Math.Pow((v2.X - v1.X), 2) + Math.Pow((v2.Y - v1.Y), 2) + Math.Pow((v2.Z - v1.Z), 2));
        }
    }
}
