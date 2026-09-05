package org.neurox.patient

import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp

class MainActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) = super.onCreate(savedInstanceState) { setContent { NeuroXApp() } }
}

private val Blue = Color(0xFF265FC5)
private val Ink = Color(0xFF172033)

@Composable fun NeuroXApp() {
    var tab by remember { mutableIntStateOf(0) }
    MaterialTheme(colorScheme = lightColorScheme(primary = Blue, background = Color(0xFFF8FAFD))) {
        Scaffold(bottomBar = { NavigationBar { listOf("Home" to Icons.Default.Home, "Activities" to Icons.Default.Favorite, "Reminders" to Icons.Default.Notifications, "Safety" to Icons.Default.Shield, "Profile" to Icons.Default.Person).forEachIndexed { i, (label, icon) -> NavigationBarItem(selected = tab == i, onClick = { tab = i }, icon = { Icon(icon, label) }, label = { Text(label) }) } } }) { padding -> if(tab == 0) Home(Modifier.padding(padding)) else Placeholder(tab, Modifier.padding(padding)) }
    }
}
@Composable private fun Home(modifier: Modifier = Modifier) = Column(modifier.fillMaxSize().padding(24.dp), verticalArrangement = Arrangement.spacedBy(18.dp)) {
    Text("Good Morning", fontSize = 20.sp, color = Color.Gray); Text("Maya", fontSize = 36.sp, fontWeight = FontWeight.Bold, color = Ink)
    Card(colors = CardDefaults.cardColors(containerColor = Blue), shape = RoundedCornerShape(24.dp), modifier = Modifier.fillMaxWidth()) { Column(Modifier.padding(24.dp), horizontalAlignment = Alignment.CenterHorizontally) { Text("Talk to NeuroX", color = Color.White, fontSize = 23.sp, fontWeight = FontWeight.Bold); Spacer(Modifier.height(13.dp)); FilledIconButton(onClick = {}, modifier = Modifier.size(78.dp), colors = IconButtonDefaults.filledIconButtonColors(containerColor = Color.White, contentColor = Blue)) { Icon(Icons.Default.Mic, "Talk to NeuroX", Modifier.size(38.dp)) }; Spacer(Modifier.height(10.dp)); Text("Tap and speak naturally", color = Color.White.copy(.88f), fontSize = 16.sp) } }
    Button(onClick = {}, modifier = Modifier.fillMaxWidth().height(68.dp), shape = RoundedCornerShape(18.dp)) { Icon(Icons.Default.PlayArrow, null, Modifier.size(30.dp)); Spacer(Modifier.width(10.dp)); Text("Start Today’s Activity", fontSize = 19.sp) }
    Text("Today’s reminders", fontSize = 21.sp, fontWeight = FontWeight.Bold); Reminder("Medication", "9:00 AM", "Done", Color(0xFF218567)); Reminder("Hydration", "10:30 AM", "Upcoming", Blue)
    Card(colors = CardDefaults.cardColors(containerColor = Color(0xFFE8F5EE)), modifier = Modifier.fillMaxWidth()) { Row(Modifier.padding(17.dp), verticalAlignment = Alignment.CenterVertically) { Icon(Icons.Default.Shield, null, tint = Color(0xFF247759)); Spacer(Modifier.width(12.dp)); Column { Text("At Home · Safe", fontWeight = FontWeight.Bold); Text("Location accuracy: Good", color = Color.DarkGray) } } }
}
@Composable private fun Reminder(title:String, time:String, status:String, color:Color) = Card(modifier=Modifier.fillMaxWidth()) { Row(Modifier.padding(17.dp), verticalAlignment=Alignment.CenterVertically) { Icon(Icons.Default.Notifications, null, tint=color); Spacer(Modifier.width(14.dp)); Column(Modifier.weight(1f)) { Text(title, fontSize=18.sp, fontWeight=FontWeight.SemiBold); Text(time, color=Color.Gray) }; Text(status, color=color, fontWeight=FontWeight.SemiBold) } }
@Composable private fun Placeholder(tab:Int, modifier:Modifier) { val names=listOf("Home","Activities","Reminders","Safety","Profile"); Box(modifier.fillMaxSize(), contentAlignment=Alignment.Center) { Text(names[tab], fontSize=26.sp, fontWeight=FontWeight.Bold) } }
