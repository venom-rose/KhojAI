import { Route, Switch } from "wouter";
import { Toaster } from "sonner";
import Home from "@/pages/Home";
import Discover from "@/pages/Discover";
import DestinationDetail from "@/pages/DestinationDetail";
import Planner from "@/pages/Planner";
import PlannerResults from "@/pages/PlannerResults";
import Contribute from "@/pages/Contribute";
import Community from "@/pages/Community";
import About from "@/pages/About";
import NotFound from "@/pages/NotFound";

export default function App() {
  return <>
    <Toaster position="bottom-right" toastOptions={{ style: { background: "#1f261e", color: "#fff", border: "0" } }} />
    <Switch>
      <Route path="/" component={Home} />
      <Route path="/discover" component={Discover} />
      <Route path="/destination/:slug" component={DestinationDetail} />
      <Route path="/planner" component={Planner} />
      <Route path="/planner/results" component={PlannerResults} />
      <Route path="/contribute" component={Contribute} />
      <Route path="/community" component={Community} />
      <Route path="/about" component={About} />
      <Route component={NotFound} />
    </Switch>
  </>;
}
