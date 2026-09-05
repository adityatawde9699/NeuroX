package org.neurox.patient

import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.compose.foundation.clickable
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
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp

class MainActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) = super.onCreate(savedInstanceState) { setContent { NeuroXApp() } }
}

private val Blue = Color(0xFF265FC5)
private val Ink = Color(0xFF172033)
private val SafeGreen = Color(0xFF218567)

@Composable fun NeuroXApp() {
    var tab by remember { mutableIntStateOf(0) }
    var activeActivity by remember { mutableStateOf<String?>(null) }
    MaterialTheme(colorScheme = lightColorScheme(primary = Blue, background = Color(0xFFF8FAFD))) {
        Scaffold(bottomBar = { NavigationBar { listOf("Home" to Icons.Default.Home, "Activities" to Icons.Default.Favorite, "Reminders" to Icons.Default.Notifications, "Safety" to Icons.Default.Shield, "Profile" to Icons.Default.Person).forEachIndexed { i, (label, icon) -> NavigationBarItem(selected = tab == i, onClick = { tab = i; activeActivity = null }, icon = { Icon(icon, label) }, label = { Text(label) }) } } }) { padding ->
            when { activeActivity == "memory" -> MemoryMatch(Modifier.padding(padding), onFinished = { activeActivity = null; tab = 1 })
                activeActivity == "objects" -> ObjectRecall(Modifier.padding(padding), onFinished = { activeActivity = null; tab = 1 })
                tab == 0 -> Home(Modifier.padding(padding), onStart = { activeActivity = "memory" })
                tab == 1 -> Activities(Modifier.padding(padding), onStartMemory = { activeActivity = "memory" }, onStartObjects = { activeActivity = "objects" })
                tab == 2 -> Reminders(Modifier.padding(padding))
                tab == 3 -> Safety(Modifier.padding(padding))
                else -> Profile(Modifier.padding(padding)) }
        }
    }
}

@Composable private fun Home(modifier: Modifier, onStart: () -> Unit) = Column(modifier.fillMaxSize().padding(24.dp), verticalArrangement = Arrangement.spacedBy(18.dp)) {
    Text("Good Morning", fontSize = 20.sp, color = Color.Gray); Text("Maya", fontSize = 36.sp, fontWeight = FontWeight.Bold, color = Ink)
    Card(colors = CardDefaults.cardColors(containerColor = Blue), shape = RoundedCornerShape(24.dp), modifier = Modifier.fillMaxWidth()) { Column(Modifier.padding(24.dp), horizontalAlignment = Alignment.CenterHorizontally) { Text("Talk to NeuroX", color = Color.White, fontSize = 23.sp, fontWeight = FontWeight.Bold); Spacer(Modifier.height(13.dp)); FilledIconButton(onClick = {}, modifier = Modifier.size(78.dp), colors = IconButtonDefaults.filledIconButtonColors(containerColor = Color.White, contentColor = Blue)) { Icon(Icons.Default.Mic, "Talk to NeuroX", Modifier.size(38.dp)) }; Spacer(Modifier.height(10.dp)); Text("Tap and speak naturally", color = Color.White.copy(.88f), fontSize = 16.sp) } }
    Button(onClick = onStart, modifier = Modifier.fillMaxWidth().height(68.dp), shape = RoundedCornerShape(18.dp)) { Icon(Icons.Default.PlayArrow, null, Modifier.size(30.dp)); Spacer(Modifier.width(10.dp)); Text("Start Today’s Activity", fontSize = 19.sp) }
    Text("Today’s reminders", fontSize = 21.sp, fontWeight = FontWeight.Bold); Reminder("Medication", "9:00 AM", "Done", SafeGreen); Reminder("Hydration", "10:30 AM", "Upcoming", Blue)
    StatusCard("At Home · Safe", "Location accuracy: Good", Icons.Default.Shield, SafeGreen)
}

@Composable private fun Activities(modifier: Modifier, onStartMemory: () -> Unit, onStartObjects: () -> Unit) = Column(modifier.fillMaxSize().padding(24.dp), verticalArrangement = Arrangement.spacedBy(15.dp)) {
    Text("Activities", fontSize = 31.sp, fontWeight = FontWeight.Bold); Text("Choose one activity for today.", color = Color.Gray, fontSize = 17.sp)
    ActivityCard("Memory Match", "Find two matching familiar objects.", Icons.Default.GridView, "Level 2", onStartMemory)
    ActivityCard("Remember the Objects", "Look, listen, then remember.", Icons.Default.Visibility, "Level 2", onStartObjects)
    ActivityCard("Pattern Completion", "Choose what comes next.", Icons.Default.Extension, "Level 2")
}

@Composable private fun MemoryMatch(modifier: Modifier, onFinished: () -> Unit) {
    val startedAt = remember { System.currentTimeMillis() }
    var first by remember { mutableStateOf<Int?>(null) }; var matched by remember { mutableStateOf(setOf<Int>()) }; var attempts by remember { mutableIntStateOf(0) }
    val symbols = listOf("☀", "☀", "☕", "☕")
    val complete = matched.size == 4
    Column(modifier.fillMaxSize().padding(24.dp), verticalArrangement = Arrangement.spacedBy(18.dp)) {
        Text("Memory Match", fontSize = 29.sp, fontWeight = FontWeight.Bold); LinearProgressIndicator(progress = { matched.size / 4f }, modifier = Modifier.fillMaxWidth()); Text(if (complete) "Well done, Maya!" else "Find the matching pictures.", fontSize = 19.sp, color = Color.Gray)
        Column(verticalArrangement = Arrangement.spacedBy(14.dp)) { (0..1).forEach { row -> Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(14.dp)) { (0..1).forEach { column -> val index = row * 2 + column; val revealed = index in matched || index == first; Card(modifier = Modifier.weight(1f).height(125.dp).clickable(enabled = !complete && index !in matched) { if (first == null) first = index else { attempts++; val selected = first!!; if (symbols[selected] == symbols[index] && selected != index) matched = matched + selected + index; first = null } }, colors = CardDefaults.cardColors(containerColor = if (revealed) Color(0xFFE8F0FF) else Blue), shape = RoundedCornerShape(18.dp)) { Box(Modifier.fillMaxSize(), contentAlignment = Alignment.Center) { Text(if (revealed) symbols[index] else "?", fontSize = 46.sp, color = if (revealed) Ink else Color.White) } } } } }
        if (complete) { val responseSeconds = ((System.currentTimeMillis() - startedAt) / 1000f).coerceAtLeast(.1f); Card(colors = CardDefaults.cardColors(containerColor = Color(0xFFE8F5EE)), modifier = Modifier.fillMaxWidth()) { Column(Modifier.padding(18.dp), horizontalAlignment = Alignment.CenterHorizontally) { Icon(Icons.Default.CheckCircle, null, tint = SafeGreen, modifier = Modifier.size(38.dp)); Text("Activity complete", fontSize = 21.sp, fontWeight = FontWeight.Bold); Text("Attempts: $attempts · Time: ${"%.1f".format(responseSeconds)} sec", color = Color.DarkGray, textAlign = TextAlign.Center); Text("Your next activity is adjusted to your performance.", color = Color.DarkGray, textAlign = TextAlign.Center, modifier = Modifier.padding(top = 6.dp)); Button(onClick = onFinished, modifier = Modifier.padding(top = 10.dp)) { Text("Continue") } } } }
    }
}

@Composable private fun ObjectRecall(modifier: Modifier, onFinished: () -> Unit) {
    var step by remember { mutableIntStateOf(0) }
    var result by remember { mutableStateOf<Boolean?>(null) }
    val startedAt = remember { System.currentTimeMillis() }
    val objects = listOf("☕ Cup", "🔑 Key", "📚 Book")
    Column(modifier.fillMaxSize().padding(24.dp), verticalArrangement = Arrangement.spacedBy(18.dp)) {
        Text("Remember the Objects", fontSize = 29.sp, fontWeight = FontWeight.Bold)
        LinearProgressIndicator(progress = { if (step == 0) .35f else .75f }, modifier = Modifier.fillMaxWidth())
        if (step == 0) {
            Text("Please look at these objects.", fontSize = 20.sp, color = Color.Gray)
            objects.forEach { objectName -> Card(modifier = Modifier.fillMaxWidth()) { Text(objectName, modifier = Modifier.padding(19.dp), fontSize = 23.sp, fontWeight = FontWeight.SemiBold) } }
            Button(onClick = { step = 1 }, modifier = Modifier.fillMaxWidth().height(65.dp), shape = RoundedCornerShape(18.dp)) { Text("I am ready", fontSize = 19.sp) }
        } else if (result == null) {
            Text("Which object did you see?", fontSize = 22.sp, fontWeight = FontWeight.SemiBold)
            Text("Choose the cup.", color = Color.Gray, fontSize = 17.sp)
            listOf("☕ Cup" to true, "🌼 Flower" to false, "🚲 Bicycle" to false).forEach { (choice, correct) -> OutlinedButton(onClick = { result = correct }, modifier = Modifier.fillMaxWidth().height(64.dp), shape = RoundedCornerShape(16.dp)) { Text(choice, fontSize = 20.sp) } }
        } else {
            val responseSeconds = ((System.currentTimeMillis() - startedAt) / 1000f).coerceAtLeast(.1f)
            Card(colors = CardDefaults.cardColors(containerColor = if (result == true) Color(0xFFE8F5EE) else Color(0xFFFFF0ED)), modifier = Modifier.fillMaxWidth()) { Column(Modifier.padding(22.dp), horizontalAlignment = Alignment.CenterHorizontally) { Icon(if (result == true) Icons.Default.CheckCircle else Icons.Default.Info, null, tint = if (result == true) SafeGreen else Color(0xFFB65A38), modifier = Modifier.size(42.dp)); Text(if (result == true) "Well done, Maya!" else "That is okay. Let’s try again tomorrow.", fontSize = 21.sp, fontWeight = FontWeight.Bold, textAlign = TextAlign.Center, modifier = Modifier.padding(top = 9.dp)); Text("Response time: ${"%.1f".format(responseSeconds)} sec", color = Color.DarkGray, modifier = Modifier.padding(top = 6.dp)); Text("Your next activity is adjusted to your performance.", color = Color.DarkGray, textAlign = TextAlign.Center, modifier = Modifier.padding(top = 8.dp)); Button(onClick = onFinished, modifier = Modifier.padding(top = 14.dp)) { Text("Continue") } } }
        }
    }
}

@Composable private fun Reminders(modifier: Modifier) { var hydrationDone by remember { mutableStateOf(false) }; Column(modifier.fillMaxSize().padding(24.dp), verticalArrangement = Arrangement.spacedBy(15.dp)) { Text("Reminders", fontSize = 31.sp, fontWeight = FontWeight.Bold); Text("Today", color = Color.Gray, fontSize = 17.sp); Reminder("Medication", "9:00 AM", "Done", SafeGreen); Reminder("Hydration", "10:30 AM", if (hydrationDone) "Done" else "Tap when done", if (hydrationDone) SafeGreen else Blue) { hydrationDone = true }; Reminder("Appointment", "Friday, 11:00 AM", "Upcoming", Blue) } }
@Composable private fun Safety(modifier: Modifier) = Column(modifier.fillMaxSize().padding(24.dp), verticalArrangement = Arrangement.spacedBy(18.dp)) { Text("Safety", fontSize = 31.sp, fontWeight = FontWeight.Bold); StatusCard("At Home · Safe", "Last updated 2 minutes ago", Icons.Default.Shield, SafeGreen); StatusCard("Expected return", "6:00 PM", Icons.Default.Schedule, Blue); OutlinedButton(onClick = {}, modifier = Modifier.fillMaxWidth().height(62.dp)) { Icon(Icons.Default.Phone, null); Spacer(Modifier.width(10.dp)); Text("I Need Help", fontSize = 18.sp) }; Button(onClick = {}, modifier = Modifier.fillMaxWidth().height(70.dp), colors = ButtonDefaults.buttonColors(containerColor = Color(0xFFBD3E39))) { Icon(Icons.Default.Warning, null); Spacer(Modifier.width(10.dp)); Text("SOS", fontSize = 22.sp) } }
@Composable private fun Profile(modifier: Modifier) = Column(modifier.fillMaxSize().padding(24.dp), verticalArrangement = Arrangement.spacedBy(16.dp)) { Text("My Profile", fontSize = 31.sp, fontWeight = FontWeight.Bold); StatusCard("Maya Devi", "72 years · Preferred language: Assamese", Icons.Default.Person, Blue); StatusCard("Caregiver", "Anita Devi", Icons.Default.People, SafeGreen) }
@Composable private fun ActivityCard(title:String, detail:String, icon: androidx.compose.ui.graphics.vector.ImageVector, level:String, onClick:()->Unit = {}) = Card(modifier=Modifier.fillMaxWidth().clickable(onClick=onClick)) { Row(Modifier.padding(19.dp), verticalAlignment=Alignment.CenterVertically) { Icon(icon, null, tint=Blue, modifier=Modifier.size(34.dp)); Spacer(Modifier.width(16.dp)); Column(Modifier.weight(1f)) { Text(title, fontSize=19.sp, fontWeight=FontWeight.SemiBold); Text(detail, color=Color.Gray) }; Text(level, color=Blue, fontWeight=FontWeight.SemiBold, fontSize=13.sp) } }
@Composable private fun Reminder(title:String, time:String, status:String, color:Color, onClick:()->Unit = {}) = Card(modifier=Modifier.fillMaxWidth().clickable(onClick=onClick)) { Row(Modifier.padding(17.dp), verticalAlignment=Alignment.CenterVertically) { Icon(Icons.Default.Notifications, null, tint=color); Spacer(Modifier.width(14.dp)); Column(Modifier.weight(1f)) { Text(title, fontSize=18.sp, fontWeight=FontWeight.SemiBold); Text(time, color=Color.Gray) }; Text(status, color=color, fontWeight=FontWeight.SemiBold) } }
@Composable private fun StatusCard(title:String, detail:String, icon: androidx.compose.ui.graphics.vector.ImageVector, color:Color) = Card(colors=CardDefaults.cardColors(containerColor=Color(0xFFF0F5FA)), modifier=Modifier.fillMaxWidth()) { Row(Modifier.padding(17.dp), verticalAlignment=Alignment.CenterVertically) { Icon(icon, null, tint=color); Spacer(Modifier.width(12.dp)); Column { Text(title, fontSize=18.sp, fontWeight=FontWeight.Bold); Text(detail, color=Color.DarkGray) } } }
